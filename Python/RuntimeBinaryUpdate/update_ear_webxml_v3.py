import os
import zipfile
import shutil
import tempfile
import json
from datetime import datetime
from lxml import etree

def create_zip_from_dir(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(source_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

def backup_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.bak_{timestamp}"
        shutil.copy(file_path, backup_path)
        print(f"📦 Backup created at: {backup_path}")

def update_web_xml_multiple(web_xml_path, updates):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(web_xml_path, parser)
    root = tree.getroot()
    nsmap = root.nsmap
    default_ns = nsmap.get(None)
    xpath_servlet = f".//{{{default_ns}}}servlet" if default_ns else ".//servlet"

    changed = False

    for update in updates:
        servlet_name = update['servlet_name']
        param_name = update['param_name']
        new_value = update['new_value']

        for servlet in root.findall(xpath_servlet):
            name_elem = servlet.find(f"{{{default_ns}}}servlet-name" if default_ns else "servlet-name")
            if name_elem is not None and name_elem.text.strip() == servlet_name:
                for init_param in servlet.findall(f"{{{default_ns}}}init-param" if default_ns else "init-param"):
                    pname = init_param.find(f"{{{default_ns}}}param-name" if default_ns else "param-name")
                    if pname is not None and pname.text.strip() == param_name:
                        pvalue = init_param.find(f"{{{default_ns}}}param-value" if default_ns else "param-value")
                        if pvalue is not None:
                            old_val = pvalue.text
                            if old_val != new_value:
                                print(f"🔧 Updating [{servlet_name} - {param_name}]: '{old_val}' ➜ '{new_value}'")
                                pvalue.text = new_value
                                changed = True
                            else:
                                print(f"ℹ️ No change needed for [{servlet_name} - {param_name}] (already '{new_value}')")

    if changed:
        tree.write(
            web_xml_path,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True
        )
        print("✅ web.xml updated with provided parameters.")
    else:
        print("⚠️ No matching servlet/param found to update.")

def find_exploded_wars(ear_dir_path):
    war_dirs = []
    for entry in os.listdir(ear_dir_path):
        full_path = os.path.join(ear_dir_path, entry)
        if os.path.isdir(full_path) and entry.lower().endswith('.war'):
            war_dirs.append(entry)
    return war_dirs

def update_ear_exploded_auto(ear_dir_path, json_config_path, output_ear_path):
    if not os.path.isdir(ear_dir_path):
        raise Exception(f"❌ EAR folder not found: {ear_dir_path}")
    if not os.path.exists(json_config_path):
        raise Exception(f"❌ JSON config not found: {json_config_path}")

    # Load JSON updates
    with open(json_config_path, "r") as f:
        updates = json.load(f)

    # Detect WAR folders
    war_dirs = find_exploded_wars(ear_dir_path)
    if not war_dirs:
        raise Exception("❌ No exploded .war folders found in EAR directory!")

    print(f"🔍 Found WAR folders: {war_dirs}")

    for war_folder in war_dirs:
        war_path = os.path.join(ear_dir_path, war_folder)
        web_xml_path = os.path.join(war_path, "WEB-INF", "web.xml")
        if os.path.exists(web_xml_path):
            update_web_xml_multiple(web_xml_path, updates)
        else:
            print(f"⚠️ Skipping {war_folder}: No web.xml found.")

    # Backup original EAR file
    if os.path.exists(output_ear_path):
        backup_file(output_ear_path)

    # Recreate EAR
    create_zip_from_dir(ear_dir_path, output_ear_path)
    print(f"✅ EAR repackaged successfully at: {output_ear_path}")

if __name__ == "__main__":
    update_ear_exploded_auto(
        ear_dir_path="/path/to/exploded/customer.ear",
        json_config_path="updates.json",
        output_ear_path="customer_updated.ear"
    )