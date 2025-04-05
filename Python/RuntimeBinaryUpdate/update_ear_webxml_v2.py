import os
import zipfile
import shutil
import tempfile
from lxml import etree

def create_zip_from_dir(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

def update_web_xml_lxml(web_xml_path, target_servlet, param_name, new_param_value):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(web_xml_path, parser)
    root = tree.getroot()

    nsmap = root.nsmap
    default_ns = nsmap.get(None)
    xpath_servlet = f".//{{{default_ns}}}servlet"

    found = False
    for servlet in root.findall(xpath_servlet):
        name_elem = servlet.find(f"{{{default_ns}}}servlet-name")
        if name_elem is not None and name_elem.text.strip() == target_servlet:
            for init_param in servlet.findall(f"{{{default_ns}}}init-param"):
                pname = init_param.find(f"{{{default_ns}}}param-name")
                if pname is not None and pname.text.strip() == param_name:
                    pvalue = init_param.find(f"{{{default_ns}}}param-value")
                    if pvalue is not None:
                        print(f"✅ Updating <param-value>: {pvalue.text} -> {new_param_value}")
                        pvalue.text = new_param_value
                        found = True
                        break

    if found:
        tree.write(
            web_xml_path,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True
        )
        print("✅ web.xml updated successfully.")
    else:
        print("⚠️ Target servlet/param not found.")

def update_ear_with_exploded_war(ear_dir_path, war_folder_name, target_servlet, param_name, new_value, output_ear_path):
    """
    ear_dir_path: path to exploded EAR directory
    war_folder_name: folder name like 'uob.war'
    output_ear_path: path to output re-zipped EAR file
    """
    if not os.path.isdir(ear_dir_path):
        raise Exception(f"❌ EAR folder not found: {ear_dir_path}")

    war_path = os.path.join(ear_dir_path, war_folder_name)
    if not os.path.isdir(war_path):
        raise Exception(f"❌ WAR folder not found: {war_path}")

    web_xml_path = os.path.join(war_path, "WEB-INF", "web.xml")
    if not os.path.isfile(web_xml_path):
        raise Exception(f"❌ web.xml not found at: {web_xml_path}")

    update_web_xml_lxml(web_xml_path, target_servlet, param_name, new_value)

    # Recreate EAR
    create_zip_from_dir(ear_dir_path, output_ear_path)
    print(f"✅ Repackaged EAR at: {output_ear_path}")
