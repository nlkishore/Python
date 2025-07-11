import os
from workflow_engine import WorkflowEngine
from nodes import parse_logs, chunk_by_time, chunk_by_session

# === Read log file from filesystem ===
def read_log_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("Log file not found: {}".format(file_path))
    with open(file_path, "r") as f:
        return f.readlines()

# === Initialize engine ===
engine = WorkflowEngine()
engine.add_node("parse", parse_logs)
engine.add_node("time_chunk", chunk_by_time)
engine.add_node("session_chunk", chunk_by_session)

engine.add_edge("parse", "time_chunk")
engine.add_edge("time_chunk", "session_chunk")

# === Load logs from file ===
log_file_path = "./logs/sample.log"  # Update path as needed
log_lines = read_log_file(log_file_path)

# === Run workflow ===
final_state = engine.run("parse", {"logs": log_lines})
print("\n✅ Final State:")
print(final_state)