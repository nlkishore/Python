import os
import zipfile
import shutil
import xml.etree.ElementTree as ET

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
    temp_ear_dir = "ear_temp"
    temp_war_dir = "war_temp"
    war_filename = None

    # Cleanup
    for d in [temp_ear_dir, temp_war_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)

    os.makedirs(temp_ear_dir, exist_ok=True)
    os.makedirs(temp_war_dir, exist_ok=True)

    # Step 1: Extract EAR but skip .war contents
    with zipfile.ZipFile(ear_path, 'r') as ear_zip:
        for item in ear_zip.infolist():
            extracted_path = os.path.join(temp_ear_dir, item.filename)
            if item.filename.endswith(".war"):
                war_filename = item.filename
                with open(extracted_path, "wb") as f:
                    f.write(ear_zip.read(item.filename))
            else:
                ear_zip.extract(item, temp_ear_dir)

    if not war_filename:
        print("❌ No .war found in the EAR file.")
        return

    war_path = os.path.join(temp_ear_dir, war_filename)

    # Step 2: Extract WAR to modify web.xml
    with zipfile.ZipFile(war_path, 'r') as war_zip:
        war_zip.extractall(temp_war_dir)

    # Step 3: Update web.xml
    web_xml_path = os.path.join(temp_war_dir, "WEB-INF", "web.xml")
    if not os.path.exists(web_xml_path):
        print("❌ web.xml not found in WAR.")
        return

    update_web_xml(web_xml_path, target_servlet, param_name, new_value)

    # Step 4: Rezip WAR
    rezip_folder(temp_war_dir, "updated.war")
    updated_war = "updated.war"
    shutil.move(updated_war, war_path)

    # Step 5: Repackage EAR
    rezip_folder(temp_ear_dir, output_ear)

    # Cleanup
    shutil.rmtree(temp_ear_dir)
    shutil.rmtree(temp_war_dir)

    print(f"✅ EAR updated and saved as: {output_ear}")


# Usage Example
if __name__ == "__main__":
    update_ear_webxml(
        ear_path="myapp.ear",
        target_servlet="portal",
        param_name="applicationRoot",
        new_value="/prodlib/GEBCUMY3/appdata",
        output_ear="myapp_updated.ear"
    )
