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
        components = ET.SubElement(command_node, "Components")
        component = ET.SubElement(components, "Component")
        ET.SubElement(component, "Name").text = "Main"
        variables = ET.SubElement(component, "Variables")
        variable = ET.SubElement(variables, "Variable")
        ET.SubElement(variable, "Name").text = "zigbee:InstantaneousDemand"

    return ET.tostring(command_node, encoding="unicode")


args = parse_arguments()

# Read config file
config = ConfigParser()
config.read('config.ini')

CLOUD_ID = config.get('rainforest', 'CLOUD_ID')
INSTALL_CODE = config.get('rainforest', 'INSTALL_CODE')
HARDWARE_ADDRESS = config.get('rainforest', 'HARDWARE_ADDRESS')

# 1. Silence SSL Warning notifications
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 3. Connection
url = "https://192.168.1.49/cgi-bin/post_manager"

headers = {
    "Content-Type": "application/xml"
}

print("Fetching and parsing metric matrices from Eagle 3...")

try:
    xml_payload = build_xml_payload(args.command, HARDWARE_ADDRESS)

    # 4. Fire the local API connection
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

    # 5. Parse the raw string tree
    root = ET.fromstring(response.text)
    
    # Check for hardware error status payload
    if root.tag == "Error":
        desc = root.find('Description')
        print(f"Eagle Core Error: {desc.text if desc is not None else 'Unknown'}")
        exit(1)

    # 6. Generate the structured terminal table layout
    print("\n" + "=" * 65)
    print(f"{'METER METRIC VARIABLE':<35} | {'CALCULATED VALUE':<18} | {'UNITS':<10}")
    print("=" * 65)

    # Define the key operational metrics we want to monitor
    target_metrics = {
        'zigbee:InstantaneousDemand': 'InstantaneousDemand',
        'zigbee:CurrentSummationDelivered': 'CurrentSummationDelivered',
        'zigbee:CurrentSummationReceived': 'CurrentSummationReceived'
    }

    # Extract and print variables directly from the XML payload
    for variable in root.findall('.//Variable'):
        name_node = variable.find('Name')
        value_node = variable.find('Value')
        units_node = variable.find('Units')
        
        if name_node is not None and name_node.text in target_metrics:
            clean_name = target_metrics[name_node.text]
            val_text = value_node.text if (value_node is not None and value_node.text) else "0.0"
            unit_text = units_node.text if (units_node is not None and units_node.text) else ""
            
            try:
                # 1. First format the string with numeric comma separators
                comma_separated_num = f"{float(val_text):,.3f}"
            except ValueError:
                comma_separated_num = val_text

            # 2. Then apply the clean trailing layout whitespace padding separately
            print(f"{clean_name:<35} | {comma_separated_num:<18} | {unit_text:<10}")

    print("=" * 65 + "\n")

except ET.ParseError as pe:
    print(f"XML Parsing Exception: {pe}")
    print("Printing fallback raw document text context:\n")
    print(response.text)
except requests.exceptions.RequestException as re:
    print(f"Network Socket Exception: {re}")
