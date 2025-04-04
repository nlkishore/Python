import os
import json

def read_properties(file_path):
    with open(file_path, 'r') as file:
        return file.readlines()


def write_properties(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)


def update_or_add_property(lines, key, value):
    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} "):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}\n")
    return lines


def batch_update_from_dict(file_path, updates: dict):
    lines = read_properties(file_path)
    for key, value in updates.items():
        lines = update_or_add_property(lines, key, value)
        print(f"✔️ {key}={value}")
    write_properties(file_path, lines)
    print(f"\n✅ Batch update complete for: {file_path}")


def batch_update_from_json(file_path, json_file):
    with open(json_file, 'r') as f:
        updates = json.load(f)
    batch_update_from_dict(file_path, updates)


# Example usage
if __name__ == "__main__":
    prop_file = "sample.properties"
    
    # Option 1: Direct dictionary input
    updates = {
        "app.name": "UpdatedApp",
        "app.version": "2.0.1",
        "db.user": "admin",
        "db.password": "supersecret"
    }
    batch_update_from_dict(prop_file, updates)

    # Option 2: From external JSON file
    # json_file = "config_update.json"
    # batch_update_from_json(prop_file, json_file)
