import os
import shutil
import xml.etree.ElementTree as ET

def update_web_xml(web_xml_path, target_servlet, param_name, new_param_value):
    tree = ET.parse(web_xml_path)
    root = tree.getroot()

    # Get namespace from root tag
    namespace = root.tag[root.tag.find("{")+1 : root.tag.find("}")]
    ns = {'ns': namespace}

    # Use the namespace in XPath
    for servlet in root.findall('ns:servlet', ns):
        name = servlet.find('ns:servlet-name', ns)
        if name is not None and name.text.strip() == target_servlet:
            for init_param in servlet.findall('ns:init-param', ns):
                pname = init_param.find('ns:param-name', ns)
                if pname is not None and pname.text.strip() == param_name:
                    pvalue = init_param.find('ns:param-value', ns)
                    if pvalue is not None:
                        print(f"Updating value from {pvalue.text} to {new_param_value}")
                        pvalue.text = new_param_value
                        tree.write(web_xml_path, encoding='utf-8', xml_declaration=True)
                        return True
    print("⚠️ Matching servlet or param not found.")
    return False

def update_exploded_ear_webxml(ear_path, war_folder_name, target_servlet, param_name, new_value):
    war_path = os.path.join(ear_path, war_folder_name)
    web_xml_path = os.path.join(war_path, "WEB-INF", "web.xml")

    if not os.path.exists(web_xml_path):
        print("❌ web.xml not found at expected location.")
        return

    updated = update_web_xml(web_xml_path, target_servlet, param_name, new_value)
    if updated:
        print(f"✅ web.xml updated successfully in {war_folder_name}")
    else:
        print(f"⚠️ No matching servlet/param found to update.")

# === Example Usage ===
if __name__ == "__main__":
    update_exploded_ear_webxml(
        ear_path="customer.ear",                # Exploded EAR path
        war_folder_name="uob.war",              # Folder name (not zipped)
        target_servlet="portal",                # <servlet-name>
        param_name="applicationRoot",           # <param-name>
        new_value="/prodlib/GEBCUMY3/appdata"   # New <param-value>
    )
