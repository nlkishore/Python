import pandas as pd
import xml.etree.ElementTree as ET

# Load the Excel file
excel_file_path = 'path_to_your_excel_file.xlsx'
df = pd.read_excel(excel_file_path)

# Extract relevant columns
element_names = df['Element Name']
mandatory_status = df['Mandatory/Optional']

# Load the XML message
xml_file_path = 'path_to_your_xml_file.xml'
tree = ET.parse(xml_file_path)
root = tree.getroot()

# Function to check if an element is present in the XML
def element_present(element_name, root):
    return root.find('.//' + element_name) is not None

# Validate elements
missing_mandatory_elements = []
for name, status in zip(element_names, mandatory_status):
    if status.lower() == 'mandatory' and not element_present(name, root):
        missing_mandatory_elements.append(name)

# Print results
if missing_mandatory_elements:
    print(f"Missing mandatory elements: {', '.join(missing_mandatory_elements)}")
else:
    print("All mandatory elements are present in the XML message.")
