#!/usr/bin/env python3
import os

import pandas as pd

CSV_FILE = "eagle3_log.csv"
PACIFIC_TIMEZONE = "America/Los_Angeles"
TARGET_DAYS = ["Sunday", "Monday"]

if not os.path.isfile(CSV_FILE):
    print(f"Error: {CSV_FILE} not found. Ensure the file is present in the working directory.")
    raise SystemExit(1)

df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()
df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True).dt.tz_convert(PACIFIC_TIMEZONE)
df["InstantaneousDemand_kW"] = pd.to_numeric(df["InstantaneousDemand_kW"], errors="coerce")
df = df.dropna(subset=["Timestamp", "InstantaneousDemand_kW"])

df["Date"] = df["Timestamp"].dt.date
df["Day"] = df["Timestamp"].dt.day_name()

daily_power = df.groupby(["Date", "Day"])["InstantaneousDemand_kW"].mean().reset_index()
weekly_power = daily_power[daily_power["Day"].isin(TARGET_DAYS)].groupby("Day").agg(
    Avg_Daily_Power_kW=("InstantaneousDemand_kW", "mean"),
    Days_Logged=("Date", "count"),
).reindex(TARGET_DAYS)

if weekly_power["Avg_Daily_Power_kW"].isna().all():
    print("No Sunday or Monday readings found in the log.")
    raise SystemExit(0)

max_value = weekly_power["Avg_Daily_Power_kW"].max()
scale_factor = 40 / max_value if max_value > 0 else 1

print("\nAVERAGE DAILY POWER (Pacific Time, Sunday-Monday)")
print("=" * 65)

for day, row in weekly_power.iterrows():
    if pd.isna(row["Avg_Daily_Power_kW"]):
        print(f"{day:<10} | No readings")
        continue

    value = row["Avg_Daily_Power_kW"]
    bar = "#" * int(value * scale_factor)
    print(f"{day:<10} | {bar:<40} {value:.3f} kW ({int(row['Days_Logged'])} days)")