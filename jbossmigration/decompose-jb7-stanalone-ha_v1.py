import xml.etree.ElementTree as ET
import os

# Path to your JBoss 7 standalone-ha.xml
input_xml = "standalone-ha.xml"
output_dir = "jboss7_modules"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Parse the XML
tree = ET.parse(input_xml)
root = tree.getroot()

# Define modules to extract (add more as needed)
modules = [
    ('profile', 'subsystem'),
    ('profile', 'datasources'),
    ('profile', 'deployments'),
    ('profile', 'jms-destinations'),
    ('profile', 'security-domains'),
    ('profile', 'socket-binding-group'),
    ('profile', 'extensions'),
    # Add admin-objects for MQ configurations
    ('profile', 'admin-objects'),
]

def write_module(module_name, elements):
    out_file = os.path.join(output_dir, f"{module_name}.xml")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        for elem in elements:
            f.write(ET.tostring(elem, encoding="unicode"))
    print(f"Extracted {module_name} to {out_file}")

# Extract and write each module
for parent_tag, module_tag in modules:
    parent = root.find(parent_tag)
    if parent is not None:
        elems = parent.findall(module_tag)
        if elems:
            write_module(module_tag, elems)

print("Decomposition complete. Review the extracted XML files in:", output_dir)