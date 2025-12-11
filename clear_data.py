import csv

LOG_FILE = "air_quality_log.csv"

# Overwrite the file with just the header row
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "gas_value", "fan_on"])

print(f"{LOG_FILE} has been cleared and reset with header.")
