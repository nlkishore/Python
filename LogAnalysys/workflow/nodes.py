# nodes.py

import re
from datetime import datetime

def parse_logs(state):
    logs = state.get("logs", [])
    parsed = []
    for line in logs:
        match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*SessionID=(\w+)", line)
        if match:
            parsed.append({
                "timestamp": datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S"),
                "session_id": match.group(2),
                "raw": line
            })
    return {"parsed_logs": parsed}

def chunk_by_time(state):
    logs = state.get("parsed_logs", [])
    chunks = {}
    for log in logs:
        key = log["timestamp"].replace(minute=(log["timestamp"].minute // 15) * 15, second=0)
        chunks.setdefault(key, []).append(log)
    return {"time_chunks": chunks}

def chunk_by_session(state):
    logs = state.get("parsed_logs", [])
    sessions = {}
    for log in logs:
        sessions.setdefault(log["session_id"], []).append(log)
    return {"session_chunks": sessions}