import os
import xml.etree.ElementTree as ET
import csv

def flatten_hierarchy(element, parent_name='', result=None):
    if result is None:
        result = []
    
    # Process current element
    current_name = element.attrib.get('name', '')
    combined_name = f"{parent_name}.{current_name}" if parent_name else current_name

    # Add current element to result
    if current_name:
        result.append((parent_name, current_name))

    # Process children recursively
    for child in element:
        flatten_hierarchy(child, combined_name, result)
    
    return result

def parse_and_flatten_xml(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    tree = ET.parse(file_path)
    root = tree.getroot()

    return flatten_hierarchy(root)

def write_to_csv(data, csv_file_path):
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(['Parent Name', 'Component Name'])
        # Write data
        for parent_name, component_name in data:
            writer.writerow([parent_name, component_name])

if __name__ == "__main__":
    xml_file_path = 'hierarchy.xml'
    csv_file_path = 'flattened_hierarchy.csv'

    try:
        flattened_data = parse_and_flatten_xml(xml_file_path)
        write_to_csv(flattened_data, csv_file_path)
        print(f"Flattened hierarchy saved to {csv_file_path}")
    except FileNotFoundError as e:
        print(e)
    except OSError as e:
        print(f"OSError: {e}")
