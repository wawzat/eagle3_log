#!/usr/bin/env python3
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
PACIFIC = ZoneInfo("America/Los_Angeles")

LOG_FILE = "/home/admin/eagle3_log/eagle3_log.csv"

if not os.path.isfile(LOG_FILE):
    print(f"Error: Target log file not found at {LOG_FILE}")
    exit(1)

def parse_row(line_str):
    """Parse a CSV row and return its Pacific timestamp and numeric values."""
    parts = line_str.strip().split(',')

    if not parts or "Timestamp" in parts or len(parts) < 3:
        return None

    try:
        timestamp = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        timestamp = timestamp.astimezone(PACIFIC)

        demand = float(parts[1])
        summation = float(parts[2])

        return timestamp, demand, summation
    except (ValueError, IndexError):
        return None


def print_current_row(record, daily_consumed, overwrite=False):
    """Print the latest row as a new persistent line, replacing only the previous daily total line."""
    timestamp, demand, summation = record
    if overwrite:
        # Move up to the previous daily total line so the new log row takes its place.
        print("\033[1A", end="")

    timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
    row = (
        f"{timestamp_text:<28} | "
        f"{demand:,.3f} kW".ljust(12) + " | " +
        f"{summation:,.3f} kWh".ljust(22)
    )
    print(f"\033[2K{row}")
    print(f"\033[2KDAILY POWER CONSUMED: {daily_consumed:,.3f} kWh", flush=True)

print("Attaching to live data stream... (Press Ctrl+C to exit)")
print("\n" + "=" * 62)
print(f"{'TIMESTAMP':<28} | {'DEMAND':<12} | {'SUMMATION DELIVERED':<22}")
print("=" * 62)

# First Pass: Find the current Pacific day's rows and range.
current_day_records = []
daily_date = None
daily_min = None
daily_max = None
with open(LOG_FILE, "r") as f:
    for line in f:
        record = parse_row(line)
        if record is None:
            continue

        timestamp, _, summation = record
        if timestamp.date() != daily_date:
            daily_date = timestamp.date()
            daily_min = summation
            daily_max = summation
            current_day_records = [record]
        else:
            daily_min = min(daily_min, summation)
            daily_max = max(daily_max, summation)
            current_day_records.append(record)

has_rendered = False
if current_day_records:
    daily_consumed = daily_max - daily_min
    for record in current_day_records:
        print_current_row(record, daily_consumed, overwrite=has_rendered)
        has_rendered = True

# Second Pass: Jump to the end and watch for live appends
with open(LOG_FILE, "r") as f:
    f.seek(0, os.SEEK_END)
    
    try:
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            record = parse_row(line)
            if record is None:
                continue

            timestamp, _, summation = record
            if timestamp.date() != daily_date:
                daily_date = timestamp.date()
                daily_min = summation
                daily_max = summation
            else:
                daily_min = min(daily_min, summation)
                daily_max = max(daily_max, summation)

            print_current_row(
                record,
                daily_max - daily_min,
                overwrite=has_rendered,
            )
            has_rendered = True
                
    except KeyboardInterrupt:
        print("\n" + "=" * 62)
        print("Detached from stream cleanly.")
