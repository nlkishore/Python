import os

def read_properties(file_path):
    with open(file_path, 'r') as file:
        return file.readlines()


def write_properties(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)


def update_property(file_path, key, value):
    lines = read_properties(file_path)
    found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} "):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    write_properties(file_path, new_lines)
    print(f"✅ Property updated: {key}={value}")


def comment_property(file_path, key):
    lines = read_properties(file_path)
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if (stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ")) and not stripped.startswith("#"):
            new_lines.append(f"# {line}")
        else:
            new_lines.append(line)

    write_properties(file_path, new_lines)
    print(f"💬 Property commented: {key}")


def add_property(file_path, key, value):
    lines = read_properties(file_path)
    for line in lines:
        if line.strip().startswith(f"{key}="):
            print(f"⚠️ Property '{key}' already exists. Use update instead.")
            return
    lines.append(f"{key}={value}\n")
    write_properties(file_path, lines)
    print(f"➕ Property added: {key}={value}")


def insert_property_before(file_path, new_key, new_value, before_key):
    lines = read_properties(file_path)
    new_lines = []
    inserted = False

    for line in lines:
        stripped = line.strip()
        if not inserted and (stripped.startswith(f"{before_key}=") or stripped.startswith(f"{before_key} ")):
            new_lines.append(f"{new_key}={new_value}\n")
            inserted = True
        new_lines.append(line)

    if not inserted:
        print(f"⚠️ Key '{before_key}' not found. Appending at the end.")
        new_lines.append(f"{new_key}={new_value}\n")

    write_properties(file_path, new_lines)
    print(f"🔀 Inserted {new_key}={new_value} before {before_key}" if inserted else f"📌 Appended {new_key}={new_value}")


# Example usage
if __name__ == "__main__":
    prop_file = "sample.properties"

    update_property(prop_file, "app.name", "CustomerApp")
    add_property(prop_file, "app.version", "1.0.3")
    comment_property(prop_file, "old.key")
    insert_property_before(prop_file, "db.user", "admin", "db.password")
