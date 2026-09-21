import argparse
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import xml.etree.ElementTree as ET
from configparser import ConfigParser


def parse_arguments():
    parser = argparse.ArgumentParser(description="Send a command to Eagle 3.")
    parser.add_argument(
        "command",
        choices=("device_list", "device_query", "device_details"),
        help="The Eagle 3 command to send.",
    )
    return parser.parse_args()


def build_xml_payload(command, hardware_address):
    command_node = ET.Element("Command")
    ET.SubElement(command_node, "Name").text = command

    if command in ("device_query", "device_details"):
        device_details = ET.SubElement(command_node, "DeviceDetails")
        ET.SubElement(device_details, "HardwareAddress").text = hardware_address

    if command == "device_query":
        # Using the <All>Y</All> shortcut block documented on page 13 
        # to fetch all operational variables at once dynamically
        components = ET.SubElement(command_node, "Components")
        ET.SubElement(components, "All").text = "Y"

    return ET.tostring(command_node, encoding="unicode")


args = parse_arguments()

# Read config file
config = ConfigParser()
config.read('config.ini')

CLOUD_ID = config.get('rainforest', 'CLOUD_ID')
INSTALL_CODE = config.get('rainforest', 'INSTALL_CODE')
HARDWARE_ADDRESS = config.get('rainforest', 'HARDWARE_ADDRESS')

# Silence SSL Warning notifications
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://192.168.1.49/cgi-bin/post_manager"

headers = {
    "Content-Type": "application/xml"
}

print(f"Executing local API command '{args.command}' on Eagle 3...")

try:
    xml_payload = build_xml_payload(args.command, HARDWARE_ADDRESS)

    response = requests.post(
        url, 
        data=xml_payload, 
        verify=False, 
        headers=headers,
        auth=HTTPBasicAuth(CLOUD_ID, INSTALL_CODE)
    )
    
    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: Communication link failed.")
        exit(1)

    root = ET.fromstring(response.text)
    
    if root.tag == "Error":
        desc = root.find('Description')
        print(f"Eagle Core Error: {desc.text if desc is not None else 'Unknown'}")
        exit(1)

    # --- Choice 1: Handle Device List ---
    if args.command == "device_list":
        print("\n" + "=" * 75)
        print(f"{'HARDWARE ADDRESS':<20} | {'MODEL ID':<20} | {'STATUS':<15} | {'MANUFACTURER':<12}")
        print("=" * 75)
        for device in root.findall('.//Device'):
            hw_addr = device.findtext('HardwareAddress', default='N/A')
            model_id = device.findtext('ModelId', default='N/A')
            status = device.findtext('ConnectionStatus', default='N/A')
            mfg = device.findtext('Manufacturer', default='N/A')
            print(f"{hw_addr:<20} | {model_id:<20} | {status:<15} | {mfg:<12}")
        print("=" * 75 + "\n")

    # --- Choice 2: Handle Device Details ---
    elif args.command == "device_details":
        print("\n" + "=" * 50)
        print(f"{'AVAILABLE DEVICE VARIABLE NAMES'}")
        print("=" * 50)
        # Device details lists variables inside component profile frames as raw text strings
        variables = root.findall('.//Variables/Variable')
        if variables:
            for variable in variables:
                print(f"- {variable.text}")
        else:
            print("No variables exposed or device profile not discovered.")
        print("=" * 50 + "\n")

    # --- Choice 3: Handle Device Query Matrix ---
    elif args.command == "device_query":
        print("\n" + "=" * 70)
        print(f"{'METER METRIC VARIABLE':<35} | {'CALCULATED VALUE':<18} | {'UNITS':<10}")
        print("=" * 70)

        target_metrics = {
            'zigbee:InstantaneousDemand': 'InstantaneousDemand',
            'zigbee:CurrentSummationDelivered': 'CurrentSummationDelivered',
            'zigbee:CurrentSummationReceived': 'CurrentSummationReceived'
        }

        for variable in root.findall('.//Variable'):
            name_node = variable.find('Name')
            value_node = variable.find('Value')
            
            if name_node is not None and name_node.text in target_metrics:
                clean_name = target_metrics[name_node.text]
                val_raw = value_node.text if (value_node is not None and value_node.text) else "0.0"
                
                # Split value from units (e.g., "21.499 kW" -> "21.499", "kW")
                val_parts = val_raw.strip().split(maxsplit=1)
                val_text = val_parts[0] if len(val_parts) > 0 else "0.0"
                unit_text = val_parts[1] if len(val_parts) > 1 else ""
                
                try:
                    comma_separated_num = f"{float(val_text):,.3f}"
                except ValueError:
                    comma_separated_num = val_text

                print(f"{clean_name:<35} | {comma_separated_num:<18} | {unit_text:<10}")

        print("=" * 70 + "\n")

except ET.ParseError as pe:
    print(f"XML Parsing Exception: {pe}")
    print("Printing fallback raw document text context:\n")
    print(response.text)
except requests.exceptions.RequestException as re:
    print(f"Network Socket Exception: {re}")