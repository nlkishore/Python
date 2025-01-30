import json
import pandas as pd
import os

file_path = "/Users/yaswitha/sonar-rules.json"

# Check if the file is empty
if os.path.exists(file_path) and os.stat(file_path).st_size == 0:
    print("❌ Error: The JSON file is empty! Please re-download it.")
    exit(1)

# Try loading JSON safely
try:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError:
    print("❌ Error: Invalid JSON format. Check the downloaded file!")
    exit(1)

# Extract Java rules
rules = data.get("rules", [])
formatted_rules = [
    {"Rule ID": rule["key"], "Name": rule["name"]}
    for rule in rules
    if "RSPEC" in rule["key"]
]

# Convert to DataFrame & Save to Excel
df = pd.DataFrame(formatted_rules)
df.to_excel("/Users/yaswitha/k8s/python/Python/Python/SonarqubeRules/SonarLint-Java-Rules.xlsx", index=False)

print("✅ Extracted SonarLint Java Rule IDs. Saved as 'SonarLint-Java-Rules.xlsx'")
