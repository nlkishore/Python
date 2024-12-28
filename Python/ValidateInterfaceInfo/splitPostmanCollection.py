import json
import os
import re

def sanitize_filename(name):
    # Replace spaces and special characters with underscores
    return re.sub(r'[\\/*?:"<>| ]', '_', name)

def split_postman_collection(collection_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(collection_file, 'r', encoding='utf-8') as file:
        collection = json.load(file)

    # Add a debug statement to ensure collection is loaded
    print("Collection loaded successfully")

    def process_items(items, base_path):
        for item in items:
            sanitized_name = sanitize_filename(item['name'])
            if 'item' in item:
                # It's a folder, process its items recursively
                folder_path = os.path.join(base_path, sanitized_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                # Recursively process the items in the folder
                process_items(item['item'], folder_path)
            else:
                # It's an individual request
                request_file = os.path.join(base_path, f"{sanitized_name}.json")
                with open(request_file, 'w', encoding='utf-8') as outfile:
                    json.dump(item, outfile, indent=4, ensure_ascii=False)
                # Add a debug statement to confirm file creation
                print(f"Created file: {request_file}")

    process_items(collection['item'], output_dir)

collection_file = 'path/to/your/postman_collection.json'
output_dir = 'path/to/output_directory'
split_postman_collection(collection_file, output_dir)