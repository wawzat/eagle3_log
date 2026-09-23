#!/usr/bin/env python3
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")

LOG_FILE = "/home/admin/eagle3_log/eagle3_log.csv"

if not os.path.isfile(LOG_FILE):
    print(f"Error: Target log file not found at {LOG_FILE}")
    exit(1)

def print_row(line_str):
    """Helper function to parse a CSV line string and print it cleanly."""
    parts = line_str.strip().split(',')
    if not parts or "Timestamp" in parts or len(parts) < 3:
        return False
    try:
        timestamp = (
            datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
            .replace(tzinfo=ZoneInfo("UTC"))
            .astimezone(PACIFIC)
            .strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        demand = float(parts[1])
        summation = float(parts[2])
        
        demand_fmt = f"{demand:,.3f} kW"
        summation_fmt = f"{summation:,.3f} kWh"
        
        print(f"{timestamp:<20} | {demand_fmt:<12} | {summation_fmt:<22}", flush=True)
        return True
    except (ValueError, IndexError):
        return False

print("Attaching to live data stream... (Press Ctrl+C to exit)")
print("\n" + "=" * 62)
print(f"{'TIMESTAMP':<20} | {'DEMAND':<12} | {'SUMMATION DELIVERED':<22}")
print("=" * 62)

# First Pass: Find and print the last existing row in the file
last_row = None
with open(LOG_FILE, "r") as f:
    for line in f:
        if line.strip():
            last_row = line

if last_row:
    print_row(last_row)

# Second Pass: Jump to the end and watch for live appends
with open(LOG_FILE, "r") as f:
    f.seek(0, os.SEEK_END)
    
    try:
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            print_row(line)
                
    except KeyboardInterrupt:
        print("\n" + "=" * 62)
        print("Detached from stream cleanly.")
