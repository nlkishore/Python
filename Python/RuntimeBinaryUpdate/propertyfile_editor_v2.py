import json

'''
Comment out existing properties (by key)
Insert new properties before a given property key, or:
If the "before key" is not found:
Add at the end (default) or
Add at the beginning
Keep original formatting, comments, and blank lines
Output the updated properties file
'''
def update_properties_file(file_path, config_path, output_path=None):
    with open(config_path, 'r') as f:
        config = json.load(f)

    with open(file_path, 'r') as f:
        lines = f.readlines()

    comment_keys = set(config.get("comment_keys", []))
    additions = config.get("add_properties", [])

    updated_lines = []
    added_keys = set()

    # Build property key -> line index mapping
    key_line_map = {}
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            key_line_map[key] = idx

    # Comment existing keys
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in comment_keys:
                lines[idx] = f"# {line}"
                print(f"🗒️ Commented out: {key}")
    
    # Handle new additions
    for entry in additions:
        key = entry["key"]
        value = entry["value"]
        before = entry.get("before")
        position = entry.get("position", "end").lower()

        new_line = f"{key}={value}\n"
        added = False

        if key in key_line_map or key in added_keys:
            continue  # Skip if already exists

        if before and before in key_line_map:
            insert_index = key_line_map[before]
            lines.insert(insert_index, new_line)
            print(f"➕ Added {key} before {before}")
            added = True
        elif position == "start":
            lines.insert(0, new_line)
            print(f"📌 Added {key} at start")
            added = True
        else:
            lines.append(new_line)
            print(f"📍 Added {key} at end")
            added = True

        if added:
            added_keys.add(key)

    # Write to output
    final_path = output_path or file_path
    with open(final_path, 'w') as f:
        f.writelines(lines)

    print(f"✅ Properties file updated: {final_path}")

update_properties_file(
    file_path="app.properties",
    config_path="config_property.json",
    output_path="app_updated.properties"
)
