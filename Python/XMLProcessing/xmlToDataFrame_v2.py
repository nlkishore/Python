import xml.etree.ElementTree as ET
import pandas as pd

# Sample XML
xml_data = """
<root>
    <parent attribute="parent_value">
        <child attribute="child1_value">child1_text</child>
        <child attribute="child2_value">
            <subchild attribute="subchild_value">subchild_text</subchild>
        </child>
    </parent>
</root>
"""

# Parse the XML
root = ET.fromstring(xml_data)

# Function to extract elements and their attributes
def parse_element(element, parent_name=''):
    elements = []
    for child in element:
        elem_name = f"{parent_name}/{child.tag}" if parent_name else child.tag
        elem_value = child.text
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
