import xml.etree.ElementTree as ET
import pandas as pd
import os

#file_path=os.path.join('data','sample.xml')

file_path='/Users/yaswitha/k8s/python/Python/Python/XMLProcessing/data/sample.xml'
# Parse the XML file
tree = ET.parse(file_path)
root = tree.getroot()

# Function to extract elements and their attributes
def parse_element(element, parent_name=''):
    elements = []
    for child in element:
        elem_name = f"{parent_name}/{child.tag}" if parent_name else child.tag
        elem_value = child.text.strip() if child.text else None
        elem_attributes = child.attrib
        elements.append({'Element Name': elem_name, 'Element Value': elem_value, **elem_attributes})
        # Recursively parse the child elements
        elements.extend(parse_element(child, elem_name))
    return elements

# Get all elements from the XML
elements = parse_element(root)

# Create DataFrame
df = pd.DataFrame(elements)

# Display the DataFrame
print(df)
