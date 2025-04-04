import zipfile
import os
import shutil
import xml.etree.ElementTree as ET

def update_context_root_in_ear(ear_path, new_context_root, output_ear_path):
    temp_dir = "temp_ear_extracted"
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # Step 1: Extract EAR
    with zipfile.ZipFile(ear_path, 'r') as ear:
        ear.extractall(temp_dir)
    
    # Step 2: Locate and update application.xml
    app_xml_path = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file == "application.xml":
                app_xml_path = os.path.join(root, file)
                break
    
    if not app_xml_path:
        print("application.xml not found in EAR")
        return

    # Step 3: Update context-root in application.xml
    tree = ET.parse(app_xml_path)
    root = tree.getroot()
    ns = {'ns': 'http://java.sun.com/xml/ns/javaee'}

    # Register namespace
    ET.register_namespace('', ns['ns'])

    for module in root.findall('ns:module', ns):
        web = module.find('ns:web', ns)
        if web is not None:
            context_root = web.find('ns:context-root', ns)
            if context_root is not None:
                print(f"Old context-root: {context_root.text}")
                context_root.text = new_context_root
                print(f"Updated context-root to: {new_context_root}")
                break

    # Save updated application.xml
    tree.write(app_xml_path, encoding='utf-8', xml_declaration=True)

    # Step 4: Repackage EAR
    shutil.make_archive("updated_ear", 'zip', temp_dir)
    shutil.move("updated_ear.zip", output_ear_path)

    # Clean up
    shutil.rmtree(temp_dir)
    print(f"Updated EAR saved to: {output_ear_path}")


# Example usage:
if __name__ == "__main__":
    ear_file_path = "sample.ear"  # Path to the input EAR file
    updated_context = "/newcontext"
    output_ear_file = "sample_updated.ear"

    update_context_root_in_ear(ear_file_path, updated_context, output_ear_file)
