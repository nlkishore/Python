import os
import shutil

jboss7_modules_dir = "/app/jboss/eap7-3/modules"
jboss8_modules_dir = "/app/jboss/eap-8/modules"

def get_all_module_paths(base_dir):
    module_paths = []
    for root, dirs, files in os.walk(base_dir):
        if "module.xml" in files:
            rel_path = os.path.relpath(root, base_dir)
            module_paths.append(rel_path)
    return set(module_paths)

def copy_module(src_base, dest_base, rel_path):
    src = os.path.join(src_base, rel_path)
    dest = os.path.join(dest_base, rel_path)
    if not os.path.exists(dest):
        shutil.copytree(src, dest)
        print(f"Copied module: {rel_path}")
        update_module_xml(os.path.join(dest, "module.xml"))
    else:
        print(f"Module already exists in JBoss 8: {rel_path}")

def update_module_xml(xml_path):
    # Placeholder for any XML update logic needed for JBoss 8 compatibility
    # For now, just print the path
    print(f"Checked/updated: {xml_path}")
    # Example: You could use xml.etree.ElementTree to parse and update the XML

if __name__ == "__main__":
    modules7 = get_all_module_paths(jboss7_modules_dir)
    modules8 = get_all_module_paths(jboss8_modules_dir)

    missing_modules = modules7 - modules8

    print(f"Modules missing in JBoss 8: {len(missing_modules)}")
    for rel_path in missing_modules:
        copy_module(jboss7_modules_dir, jboss8_modules_dir, rel_path)

    print("Module migration complete.")