#!/usr/bin/env python3
import os

import pandas as pd

CSV_FILE = "eagle3_log.csv"
PACIFIC_TIMEZONE = "America/Los_Angeles"

if not os.path.isfile(CSV_FILE):
    print(f"Error: {CSV_FILE} not found. Ensure the file is present in the working directory.")
    raise SystemExit(1)

df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()
df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True).dt.tz_convert(PACIFIC_TIMEZONE)
df["SummationDelivered_kWh"] = pd.to_numeric(df["SummationDelivered_kWh"], errors="coerce")
df["InstantaneousDemand_kW"] = pd.to_numeric(df["InstantaneousDemand_kW"], errors="coerce")

demand_df = df.dropna(subset=["Timestamp", "InstantaneousDemand_kW"]).copy()
demand_df["Date"] = demand_df["Timestamp"].dt.date
daily_demand = demand_df.groupby("Date")["InstantaneousDemand_kW"].agg(
    Minimum="min",
    Average="mean",
    Maximum="max",
).reset_index()

df = df.dropna(subset=["Timestamp", "SummationDelivered_kWh"])
df = df[df["SummationDelivered_kWh"] > 0]

df["Date"] = df["Timestamp"].dt.date
daily_consumption = df.groupby("Date")["SummationDelivered_kWh"].agg(
    Minimum="min",
    Maximum="max",
).reset_index()
daily_consumption["Consumption_kWh"] = (
    daily_consumption["Maximum"] - daily_consumption["Minimum"]
)
daily_consumption = daily_consumption.drop(columns=["Minimum", "Maximum"]).merge(
    daily_demand,
    on="Date",
    how="left",
)

if daily_consumption.empty:
    print("No valid meter readings found in the log.")
    raise SystemExit(0)

max_value = daily_consumption["Consumption_kWh"].max()
scale_factor = 40 / max_value if max_value > 0 else 1

print("\nACTUAL DAILY CONSUMPTION (Pacific Time)")
print("=" * 120)

for _, row in daily_consumption.iterrows():
    value = row["Consumption_kWh"]
    bar = "#" * int(value * scale_factor)
    day_of_week = row["Date"].strftime("%A")
    print(
        f"{day_of_week:<10} {row['Date']} | {bar:<40} "
        f"{value:.3f} kWh consumed | Demand min/avg/max: "
        f"{row['Minimum']:.3f}/{row['Average']:.3f}/{row['Maximum']:.3f} kW"
    )