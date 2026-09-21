import requests
from requests.auth import HTTPBasicAuth
import urllib3
import xml.etree.ElementTree as ET
import csv
import os
import time
from datetime import datetime
from configparser import ConfigParser

# Read config file
config = ConfigParser()
config.read('config.ini')

CLOUD_ID = config.get('rainforest', 'CLOUD_ID')
INSTALL_CODE = config.get('rainforest', 'INSTALL_CODE')
HARDWARE_ADDRESS = config.get('rainforest', 'HARDWARE_ADDRESS')

# 1. Silence SSL Warning notifications
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2. Setup structural parameters
csv_file = "eagle3_log.csv"
target_metrics = {
    'zigbee:InstantaneousDemand': 'InstantaneousDemand',
    'zigbee:CurrentSummationDelivered': 'CurrentSummationDelivered',
    'zigbee:CurrentSummationReceived': 'CurrentSummationReceived'
}

# 3. Connection Parameter
url = "https://192.168.1.49/cgi-bin/post_manager"

print(f"Starting infinite logger loop. Logging to {csv_file}... Press Ctrl+C to stop.")

# --- INFINITE WHILE LOOP WITH FIXED INTERVAL ANCHORING ---
while True:
    # 1. Anchor the loop start timestamp immediately
    loop_start = time.time()
    current_time = datetime.fromtimestamp(loop_start).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        xml_payload = f"""<Command>
  <Name>device_query</Name>
  <DeviceDetails>
    <HardwareAddress>{HARDWARE_ADDRESS}</HardwareAddress>
  </DeviceDetails>
  <Components>
    <All>Y</All>
  </Components>
</Command>"""

        response = requests.post(
            url, 
            data=xml_payload, 
            verify=False, 
            headers={"Content-Type": "application/xml"},  
            auth=HTTPBasicAuth(CLOUD_ID, INSTALL_CODE),
            timeout=10  
        )
        
        if response.status_code != 200:
            print(f"[{current_time}] HTTP Connection Issue: Error code {response.status_code}.")
        else:
            root = ET.fromstring(response.text)
            
            if root.tag == "Error":
                desc = root.find('Description')
                print(f"[{current_time}] Eagle Device reported internal error: {desc.text if desc is not None else 'Unknown'}")
            else:
                row_data = {
                    'InstantaneousDemand': '0.0',
                    'CurrentSummationDelivered': '0.0',
                    'CurrentSummationReceived': '0.0'
                }

                for variable in root.findall('.//Variable'):
                    name_node = variable.find('Name')
                    value_node = variable.find('Value')
                    if name_node is not None and name_node.text in target_metrics:
                        clean_name = target_metrics[name_node.text]
                        if value_node is not None and value_node.text:
                            row_data[clean_name] = value_node.text

                try:
                    demand_fmt = f"{float(row_data['InstantaneousDemand']):,.3f}"
                    summation_fmt = f"{float(row_data['CurrentSummationDelivered']):,.3f}"
                except ValueError:
                    demand_fmt = row_data['InstantaneousDemand']
                    summation_fmt = row_data['CurrentSummationDelivered']

                file_exists = os.path.isfile(csv_file)
                with open(csv_file, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Timestamp', 'InstantaneousDemand_kW', 'SummationDelivered_kWh', 'SummationReceived_kWh'])
                    
                    writer.writerow([
                        current_time, 
                        row_data['InstantaneousDemand'], 
                        row_data['CurrentSummationDelivered'], 
                        row_data['CurrentSummationReceived']
                    ])

                print(f"[{current_time}] Logged data row -> Demand: {demand_fmt:<8} kW | Cumulative Total: {summation_fmt:<12} kWh")

    except requests.exceptions.RequestException as re:
        print(f"[{current_time}] Network Connection Exception: ({re})")
    except ET.ParseError as pe:
        print(f"[{current_time}] XML Parsing Exception: ({pe})")
    except KeyboardInterrupt:
        print(f"\n[{current_time}] Execution halted by user command. Exiting logger cleanly.")
        break
    except Exception as general_err:
        print(f"[{current_time}] Unexpected operational loop issue encountered: {general_err}")

    # --- TRUE 60-SECOND INTERVAL TIMING ---
    # Calculate execution time and sleep precisely for the remainder of the 60 seconds
    elapsed = time.time() - loop_start
    sleep_duration = max(0.0, 60.0 - elapsed)
    time.sleep(sleep_duration)
