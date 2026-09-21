# Eagle 3 Energy Monitor Log Tools

Utilities for polling a Rainforest Eagle 3 energy monitor's local API, logging power usage data, and analyzing/tailing the resulting logs.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Configure device credentials in `config.ini`:
   ```ini
   [rainforest]
   CLOUD_ID = <cloud id>
   INSTALL_CODE = <install code>
   HARDWARE_ADDRESS = <electric meter hardware address>
   ```

## Programs

### `eagle3.py`
One-shot query tool. Connects to the Eagle 3 device's local API, fetches current meter readings (instantaneous demand, cumulative delivered/received summation), and prints them as a formatted table to the console. Useful for a quick status check.

```
python eagle3.py
```

### `eagle3_command.py`
Command tool for sending supported commands to the Eagle 3 device's local API. The available commands are `device_list`, `device_query`, and `device_details`.

```
python ealge3_command.py device_list
python ealge3_command.py device_query
python ealge3_command.py device_details
```

### `eagle3_log.py`
Continuous logger. Runs an infinite loop that queries the Eagle 3 device every 60 seconds (anchored to a fixed interval) and appends the results to `eagle3_log.csv`. Creates the CSV with a header row if it doesn't already exist. Stop with `Ctrl+C`.

```
python eagle3_log.py
```

### `tail_log.py`
Live log viewer, similar to `tail -f`. Prints the most recent row of `eagle3_log.csv`, then watches the file and prints new rows as `eagle3_log.py` appends them. Update `LOG_FILE` in the script if your log path differs from the default (`/home/admin/eagle3/eagle3_log.csv`).

```
python tail_log.py
```

### `analyze_power.py`
Offline analysis tool. Reads `eagle3_log.csv`, computes true hourly energy consumption using the odometer-delta method (difference in cumulative summation readings), and prints:
- A text bar chart of average consumption by hour of day
- Total estimated daily consumption
- A summary table of average consumption and demand per hour

```
python analyze_power.py
```

## Files

| File | Purpose |
|---|---|
| `config.ini` | Device credentials used by `eagle3.py` and `eagle3_log.py` |
| `ealge3_command.py` | Sends supported commands to the Eagle 3 device's local API |
| `eagle3_log.csv` | CSV data log produced by `eagle3_log.py` (generated at runtime) |
| `requirements.txt` | Python package dependencies |
