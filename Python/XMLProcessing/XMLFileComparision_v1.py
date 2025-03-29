''' Comparing Keys and report missing keys in eithet and publish the values as Report'''
import xml.etree.ElementTree as ET
import pandas as pd

def parse_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    elements = {}
    
    def recursive_parse(element, parent_path=""):
        for child in element:
            path = f"{parent_path}/{child.tag}" if parent_path else child.tag
            elements[path] = child.text
            recursive_parse(child, path)
    
    recursive_parse(root)
    return elements

def compare_xml(file1, file2):
    elements1 = parse_xml(file1)
    elements2 = parse_xml(file2)
    
    common_keys = {k: (elements1[k], elements2[k]) for k in elements1 if k in elements2}
    missing_in_file1 = {k: elements2[k] for k in elements2 if k not in elements1}
    missing_in_file2 = {k: elements1[k] for k in elements1 if k not in elements2}
    
    return common_keys, missing_in_file1, missing_in_file2

def create_excel_report(common, missing1, missing2, output_file):
    df_common = pd.DataFrame([(k, v, v) for k, v in common.items()], columns=['Element', 'Value in File 1', 'Value in File 2'])
    df_missing1 = pd.DataFrame(list(missing1.items()), columns=['Element', 'Value'])
    df_missing2 = pd.DataFrame(list(missing2.items()), columns=['Element', 'Value'])
    
    with pd.ExcelWriter(output_file) as writer:
        df_common.to_excel(writer, sheet_name='Common Elements', index=False)
        df_missing1.to_excel(writer, sheet_name='Missing in File 1', index=False)
        df_missing2.to_excel(writer, sheet_name='Missing in File 2', index=False)

# Example usage
file1 = 'path/to/your/file1.xml'
file2 = 'path/to/your/file2.xml'
common_elements, missing_in_file1, missing_in_file2 = compare_xml(file1, file2)
create_excel_report(common_elements, missing_in_file1, missing_in_file2, 'comparison_report.xlsx')

print("Comparison report generated successfully.")