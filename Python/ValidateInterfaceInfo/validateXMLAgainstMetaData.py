import pandas as pd
import xml.etree.ElementTree as ET

# Load the Excel file
excel_file = "elements_definition.xlsx"
df = pd.read_excel(excel_file)

# Parse the XML file
xml_file = "input.xml"
tree = ET.parse(xml_file)
root = tree.getroot()

# Function to validate elements
def validate_elements(root, elements):
    missing_elements = []
    for index, row in elements.iterrows():
        element_path = row['ElementPath']
        is_mandatory = row['Mandatory']
        element = root.find(element_path)
        if is_mandatory == "Yes" and element is None:
            missing_elements.append(element_path)
    return missing_elements

# Validate the elements
missing_elements = validate_elements(root, df)
if missing_elements:
    print("Missing mandatory elements:")
    for elem in missing_elements:
        print(elem)
else:
    print("All mandatory elements are present.")

# Example Excel format:
# | ElementPath       | Mandatory |
# |-------------------|-----------|
# | ./root/element1   | Yes       |
# | ./root/element2   | No        |
# | ./root/element3   | Yes       |
