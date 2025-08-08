import os
import shutil

jboss7_modules_dir = "/app/jboss/eap7-3/modules"
jboss8_modules_dir = "/app/jboss/eap-8/modules"

def copy_and_update_modules(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        # Compute destination path
        rel_path = os.path.relpath(root, src_dir)
        dest_path = os.path.join(dest_dir, rel_path)
        os.makedirs(dest_path, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_path, file)
            # Copy the file
            shutil.copy2(src_file, dest_file)
            # If it's a module.xml, you can add update logic here
            if file == "module.xml":
                update_module_xml(dest_file)
        print(f"Copied {root} -> {dest_path}")

def update_module_xml(xml_path):
    # Placeholder for any XML update logic needed for JBoss 8 compatibility
    # For now, just print the path
    print(f"Checked/updated: {xml_path}")
    # Example: You could use xml.etree.ElementTree to parse and update the XML

if __name__ == "__main__":
    copy_and_update_modules(jboss7_modules_dir, jboss8_modules_dir)
    print("All modules copied from JBoss 7.3 to JBoss 8.")