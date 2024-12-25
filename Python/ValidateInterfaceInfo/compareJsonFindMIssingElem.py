import json

# Load JSON data from files
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to compare two JSON objects and find missing elements
def compare_json(json1, json2, path=''):
    missing_in_json1 = {}
    missing_in_json2 = {}

    for key in json1:
        if key not in json2:
            missing_in_json2[path + key] = json1[key]
        elif isinstance(json1[key], dict) and isinstance(json2[key], dict):
            missing_1, missing_2 = compare_json(json1[key], json2[key], path + key + '.')
            missing_in_json1.update(missing_1)
            missing_in_json2.update(missing_2)

    for key in json2:
        if key not in json1:
            missing_in_json1[path + key] = json2[key]

    return missing_in_json1, missing_in_json2

# Paths to your JSON files
file_path_1 = 'path_to_first_json_file.json'
file_path_2 = 'path_to_second_json_file.json'

# Load JSON data
json_data_1 = load_json(file_path_1)
json_data_2 = load_json(file_path_2)

# Compare JSON data
missing_in_1, missing_in_2 = compare_json(json_data_1, json_data_2)

# Print results
print(f"Elements missing in the first JSON file: {missing_in_1}")
print(f"Elements missing in the second JSON file: {missing_in_2}")
