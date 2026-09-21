#!/usr/bin/env python3
import pandas as pd
import os

CSV_FILE = "eagle3_log.csv"

if not os.path.isfile(CSV_FILE):
    print(f"Error: {CSV_FILE} not found. Ensure the file is present in the working directory.")
    exit(1)

# 1. Load and clean the CSV dataset
df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df = df.sort_values('Timestamp')

# Filter out any faulty 0.0 odometer rows before calculating math boundaries
df = df[df['SummationDelivered_kWh'] > 0.0]

# 2. Extract specific grouping targets
df['DateHourKey'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:00')
df['HourOfDay'] = df['Timestamp'].dt.hour

# 3. Step A: Find the net consumption within EACH unique calendar hour block
hourly_chunks = df.groupby('DateHourKey').agg(
    Odometer_Start=('SummationDelivered_kWh', 'first'),
    Odometer_End=('SummationDelivered_kWh', 'last'),
    Avg_Demand_kW=('InstantaneousDemand_kW', 'mean'),
    Hour_Of_Day=('HourOfDay', 'first')
).reset_index()

# Calculate the actual kWh used purely inside that specific 60-minute window
hourly_chunks['Consumption_kWh'] = hourly_chunks['Odometer_End'] - hourly_chunks['Odometer_Start']

# 4. Step B: Average those clean hourly units by raw hour (0-23) across all logged days
hourly_profile = hourly_chunks.groupby('Hour_Of_Day').agg(
    Avg_Consumption_kWh=('Consumption_kWh', 'mean'),
    Avg_Demand_kW=('Avg_Demand_kW', 'mean')
).reset_index()

hourly_profile = hourly_profile.sort_values('Hour_Of_Day')

# 5. Render a Pure Text Bar Chart for Avg Consumption (kWh)
print("\n" + "=" * 75)
print("TYPICAL HOURLY NET CONSUMPTION PROFILE (kWh)")
print("=" * 75)

max_val = hourly_profile['Avg_Consumption_kWh'].max()
scale_factor = 40 / max_val if max_val > 0 else 1

for _, row in hourly_profile.iterrows():
    h_lbl = f"{int(row['Hour_Of_Day']):02d}:00"
    val = row['Avg_Consumption_kWh']
    
    bar_length = int(val * scale_factor)
    bar_str = "█" * bar_length
    
    print(f"{h_lbl:<6} | {bar_str:<40} {val:.3f} kWh")

# Calculate Total Daily Footprint by summing your typical hourly baselines
total_daily_kwh = hourly_profile['Avg_Consumption_kWh'].sum()

print("\n" + "=" * 65)
print(f"TOTAL ESTIMATED DAILY CONSUMPTION: {total_daily_kwh:,.3f} kWh")
print("=" * 65)

# 6. Generate the Structured CLI Data Table
print("\n" + "=" * 65)
print(f"{'HOUR OF DAY':<15} | {'AVG CONSUMPTION (kWh)':<22} | {'AVG DEMAND (kW)':<15}")
print("=" * 65)

for _, row in hourly_profile.iterrows():
    h_lbl = f"{int(row['Hour_Of_Day']):02d}:00"
    print(f"{h_lbl:<15} | {row['Avg_Consumption_kWh']:<22,.3f} | {row['Avg_Demand_kW']:<15,.3f}")

print("=" * 65 + "\n")