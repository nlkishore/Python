###pip install pandas xmltodict openpyxl
import pandas as pd
import xml.etree.ElementTree as ET
import json
import xmltodict

# Function to convert JSON to XML
def json_to_xml(json_obj, root_tag):
    root = ET.Element(root_tag)
    for key, value in json_obj.items():
        child = ET.SubElement(root, key)
        child.text = str(value)
    return ET.tostring(root, encoding='unicode')

# Load metadata from Excel
metadata_file = "metadata.xlsx"
metadata_df = pd.read_excel(metadata_file)

# Load JSON message from file
json_file = "message.json"
with open(json_file, 'r') as file:
    json_message = json.load(file)

# Convert JSON to XML
xml_string = json_to_xml(json_message, 'root')
root = ET.fromstring(xml_string)

# Function to validate XML elements
def validate_xml(root, metadata_df):
    missing_elements = []
    for _, row in metadata_df.iterrows():
        element_path = row['ElementPath']
        json_key = row['JSONKey']
        is_mandatory = row['Mandatory']
        
        # Check if JSON key exists
        if is_mandatory == "Yes" and json_key not in json_message:
            missing_elements.append(json_key)
            continue
        
        # Check if XML element exists
        element = root.find(element_path.replace("/root", "."))
        if is_mandatory == "Yes" and element is None:
            missing_elements.append(element_path)
    
    return missing_elements

# Validate the XML elements
missing_elements = validate_xml(root, metadata_df)
if missing_elements:
    print("Missing mandatory elements:")
    for elem in missing_elements:
        print(elem)
else:
    print("All mandatory elements are present.")
