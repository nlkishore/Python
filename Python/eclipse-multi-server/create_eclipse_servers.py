import os
import xml.etree.ElementTree as ET

# Configuration
ECLIPSE_WORKSPACE = r"C:\Projects\eclipse\workspace"
SERVER_CONFIG = os.path.join(ECLIPSE_WORKSPACE, r".metadata\.plugins\org.eclipse.wst.server.core\servers.xml")
TOMCAT_BASE_DIR = r"C:\Projects\tomcat"

# Base ports (incremented for each instance)
HTTP_PORT = 8080
HTTPS_PORT = 8443
AJP_PORT = 8009

# Get all Tomcat instances
tomcat_instances = [d for d in os.listdir(TOMCAT_BASE_DIR) if os.path.isdir(os.path.join(TOMCAT_BASE_DIR, d))]

if not tomcat_instances:
    print("No Tomcat instances found!")
    exit()

print("Detected Tomcat instances:", tomcat_instances)

# Ensure `servers.xml` exists
if not os.path.exists(SERVER_CONFIG):
    print("Creating Eclipse server configuration...")
    root = ET.Element("servers")
    tree = ET.ElementTree(root)
    tree.write(SERVER_CONFIG)

# Load existing `servers.xml`
tree = ET.parse(SERVER_CONFIG)
root = tree.getroot()

# Remove existing Tomcat entries
for server in root.findall("server"):
    root.remove(server)

# Process each Tomcat instance
for i, tomcat_name in enumerate(tomcat_instances):
    tomcat_path = os.path.join(TOMCAT_BASE_DIR, tomcat_name)

    # Assign unique ports
    http_port = HTTP_PORT + i + 1
    https_port = HTTPS_PORT + i + 1
    ajp_port = AJP_PORT + i + 1

    print(f"Configuring {tomcat_name} with ports: HTTP={http_port}, HTTPS={https_port}, AJP={ajp_port}")

    # Add to Eclipse `servers.xml`
    server_elem = ET.SubElement(root, "server", {
        "id": tomcat_name,
        "name": tomcat_name,
        "runtime": "Apache Tomcat",
        "path": tomcat_path
    })
    ET.SubElement(server_elem, "port", {"name": "HTTP", "value": str(http_port)})
    ET.SubElement(server_elem, "port", {"name": "HTTPS", "value": str(https_port)})
    ET.SubElement(server_elem, "port", {"name": "AJP", "value": str(ajp_port)})

    # Modify Tomcat `server.xml`
    server_xml_path = os.path.join(tomcat_path, "conf", "server.xml")
    if os.path.exists(server_xml_path):
        tree_tomcat = ET.parse(server_xml_path)
        root_tomcat = tree_tomcat.getroot()

        for connector in root_tomcat.findall(".//Connector"):
            port_attr = connector.get("port")
            if port_attr == "8080":
                connector.set("port", str(http_port))
            elif port_attr == "8443":
                connector.set("port", str(https_port))
            elif port_attr == "8009":
                connector.set("port", str(ajp_port))

        tree_tomcat.write(server_xml_path)
    else:
        print(f"WARNING: {server_xml_path} not found!")

# Save updated `servers.xml`
tree.write(SERVER_CONFIG)
print("Eclipse servers updated successfully!")
