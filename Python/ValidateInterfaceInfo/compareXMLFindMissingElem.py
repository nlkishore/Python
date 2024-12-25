import xml.etree.ElementTree as ET

# Function to extract all element tags from an XML file
def extract_elements(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    elements = set()

    def recurse_tree(node):
        elements.add(node.tag)
        for child in node:
            recurse_tree(child)
    
    recurse_tree(root)
    return elements

# Paths to your XML files
file_path_1 = 'path_to_first_xml_file.xml'
file_path_2 = 'path_to_second_xml_file.xml'

# Extract elements from both XML files
elements_1 = extract_elements(file_path_1)
elements_2 = extract_elements(file_path_2)

# Find missing elements
missing_in_1 = elements_2 - elements_1
missing_in_2 = elements_1 - elements_2

# Print results
print(f"Elements missing in the first XML file: {missing_in_1}")
print(f"Elements missing in the second XML file: {missing_in_2}")
