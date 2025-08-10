import xml.etree.ElementTree as ET

def update_module_xml(xml_path):
    if not os.path.exists(xml_path):
        print(f"module.xml not found: {xml_path}")
        return

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Example: Update the namespace if needed
        old_ns = "urn:jboss:module:1.3"
        new_ns = "urn:jboss:module:1.9"
        if root.tag.startswith("{"):
            ns_uri = root.tag.split("}")[0][1:]
            if ns_uri == old_ns:
                print(f"Updating namespace in {xml_path}")
                root.tag = root.tag.replace(old_ns, new_ns)

        # Example: Print dependencies (for review or further automation)
        for dep in root.findall(".//dependencies/module"):
            dep_name = dep.attrib.get("name")
            print(f"  Dependency found in {xml_path}: {dep_name}")

        # Write back the updated XML
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        print(f"Updated: {xml_path}")

    except Exception as e:
        print(f"Error updating {xml_path}: {e}")