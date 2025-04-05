import os
import zipfile
import shutil
import xml.etree.ElementTree as ET
import platform

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def rezip_folder(folder_path, output_zip):
    base_name = os.path.splitext(output_zip)[0]
    shutil.make_archive(base_name, 'zip', folder_path)
    if os.path.exists(output_zip):
        os.remove(output_zip)
    os.rename(base_name + ".zip", output_zip)


def update_web_xml(web_xml_path, target_servlet, param_name, new_param_value):
    tree = ET.parse(web_xml_path)
    root = tree.getroot()

    for servlet in root.findall('servlet'):
        servlet_name = servlet.find('servlet-name')
        if servlet_name is not None and servlet_name.text.strip() == target_servlet:
            for init_param in servlet.findall('init-param'):
                param = init_param.find('param-name')
                if param is not None and param.text.strip() == param_name:
                    value_node = init_param.find('param-value')
                    if value_node is not None:
                        print(f"Old value: {value_node.text}")
                        value_node.text = new_param_value
                        print(f"Updated value: {new_param_value}")
                        break
    tree.write(web_xml_path, encoding='utf-8', xml_declaration=True)


def update_ear_webxml(ear_path, target_servlet, param_name, new_value, output_ear):
    temp_dir = "ear_temp"
    war_temp_dir = "war_temp"

    # Cleanup old temp dirs
    for folder in [temp_dir, war_temp_dir]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    os.makedirs(temp_dir)
    os.makedirs(war_temp_dir)

    # Step 1: Extract EAR
    extract_zip(ear_path, temp_dir)

    # Step 2: Find WAR file
    war_file = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".war"):
                war_file = os.path.join(root, file)
                break

    if not war_file:
        print("❌ WAR file not found in EAR.")
        return

    # Step 3: Extract WAR
    extract_zip(war_file, war_temp_dir)

    # Step 4: Locate and update web.xml
    web_xml_path = os.path.join(war_temp_dir, "WEB-INF", "web.xml")
    if not os.path.exists(web_xml_path):
        print("❌ web.xml not found inside WAR.")
        return

    update_web_xml(web_xml_path, target_servlet, param_name, new_value)

    # Step 5: Repackage WAR
    updated_war_path = os.path.join(temp_dir, os.path.basename(war_file))
    rezip_folder(war_temp_dir, updated_war_path)

    # Step 6: Repackage EAR
    rezip_folder(temp_dir, output_ear)

    # Cleanup
    shutil.rmtree(temp_dir)
    shutil.rmtree(war_temp_dir)

    print(f"✅ EAR file updated and saved to: {output_ear}")


# Usage example
if __name__ == "__main__":
    input_ear = "myapp.ear"
    output_ear = "myapp_updated.ear"
    update_ear_webxml(
        ear_path=input_ear,
        target_servlet="portal",
        param_name="applicationRoot",
        new_value="/prodlib/GEBCUMY3/appdata",
        output_ear=output_ear
    )
