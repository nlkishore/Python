import configparser
import pandas as pd
import re
from dateutil import parser

# === Load Configuration ===
config = configparser.ConfigParser()
config.read("config.ini")

log_path = config.get("log", "file_path")
mode = config.get("chunking", "mode")
interval = config.getint("chunking", "time_interval_minutes")
session_pattern = config.get("session", "pattern")

# === Read Log File ===
with open(log_path, "r") as f:
    log_lines = f.readlines()

# === Parse Logs ===
def parse_logs(lines):
    data = []
    for line in lines:
        try:
            timestamp = parser.parse(" ".join(line.split()[:2]))
            session_id_match = re.search(session_pattern, line)
            session_id = session_id_match.group(1) if session_id_match else "unknown"
            message = " ".join(line.split()[2:])
            data.append({"timestamp": timestamp, "session_id": session_id, "message": message})
        except Exception as e:
            print(f"Skipping line due to error: {e}")
    return pd.DataFrame(data)

df = parse_logs(log_lines)

# === Chunking Logic ===
if mode == "time":
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    chunks = df.groupby(pd.Grouper(key='timestamp', freq=f"{interval}Min"))
    for i, (chunk_time, chunk_df) in enumerate(chunks):
        print(f"\n--- Time Chunk {i+1} ({chunk_time}) ---")
        print(chunk_df)
elif mode == "session":
    sessions = df.groupby('session_id')
    for session_id, session_df in sessions:
        print(f"\n=== Session: {session_id} ===")
        print(session_df[['timestamp', 'message']])
else:
    print("❌ Invalid chunking mode in config.ini")