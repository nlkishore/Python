import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Schema Recovery Tool
# Scans Torque 3.x 'Base*Peer.java' and 'Base*.java' files to reconstruct schema.xml.
# Best Effort: Mappings may require manual adjustment.

def analyze_directory(source_dir):
    tables = {}

    print(f"Scanning {source_dir}...")

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.startswith("Base") and file.endswith("Peer.java"):
                # Found a Peer class (Table definition)
                peer_path = os.path.join(root, file)
                base_obj_name = file.replace("Peer.java", "") # BaseAuthor
                
                # Check if the Object class exists
                obj_path = os.path.join(root, base_obj_name + ".java")
                if os.path.exists(obj_path):
                    table_data = parse_peer_and_object(peer_path, obj_path)
                    if table_data:
                        tables[table_data['name']] = table_data

    return tables

def parse_peer_and_object(peer_path, obj_path):
    table_name = None
    columns = []
    
    # 1. Parse Peer for Table Name and Column Names
    with open(peer_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
        # Regex for TABLE_NAME
        tn_match = re.search(r'TABLE_NAME\s*=\s*"(.*)"', content)
        if tn_match:
            table_name = tn_match.group(1)
        else:
            return None # Cannot find table name

        # Scan for Column Constants: public static final String COL_NAME = "TABLE.COL_NAME";
        # We want the 'COL_NAME' part from the SQL mapping.
        # Actually in Torque 3: public static final String COLUMN_NAME = "TABLE_NAME.COLUMN_NAME";
        col_matches = re.findall(r'String\s+([A-Z0-9_]+)\s*=\s*".*\.([A-Z0-9_]+)"', content)
        
        for java_const, sql_col in col_matches:
            if java_const == "TABLE_NAME": continue
            columns.append({'name': sql_col, 'javaName': java_const, 'type': 'VARCHAR'}) # Default type

    # 2. Parse Object for Data Types (simple heuristic)
    with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
        obj_content = f.read()
        
        for col in columns:
            # Heuristic: Convert CONST_NAME to CamelCase logic or try to find usage
            # Easier: Scan for getters. 
            # If column is "AUTHOR_ID", getter might be "getAuthorId"
            
            # Simple converter for SQL naming to CamelCase
            parts = col['name'].split('_')
            camel = "".join(x.title() for x in parts) # AuthorId
            
            # Regex for getter: public (int|String|Date) getAuthorId()
            # We look for "get" + camel
            getter_pattern = re.compile(r'public\s+([a-zA-Z0-9_<>]+)\s+get' + re.escape(camel) + r'\(')
            match = getter_pattern.search(obj_content)
            
            if match:
                java_type = match.group(1)
                col['type'] = map_java_to_sql(java_type)
                if col['type'] == 'INTEGER':
                    # Heuristic: If it's an ID and Integer, assume PK for now
                    if 'ID' in col['name']:
                        col['primaryKey'] = 'true'

    # 3. Parse MapBuilder for ID Method (if exists)
    map_builder_path = peer_path.replace("Peer.java", "MapBuilder.java")
    if os.path.exists(map_builder_path):
        with open(map_builder_path, 'r', encoding='utf-8', errors='ignore') as f:
            mb_content = f.read()
            if 'setPrimaryKeyMethod(TableMap.ID_BROKER)' in mb_content or '"idbroker"' in mb_content:
                columns[0]['idMethod'] = 'idbroker' # Mark on first column/table
            elif 'setPrimaryKeyMethod(TableMap.NATIVE)' in mb_content or '"native"' in mb_content:
                columns[0]['idMethod'] = 'native'
            elif 'setPrimaryKeyMethod(TableMap.NONE)' in mb_content or '"none"' in mb_content:
                columns[0]['idMethod'] = 'none'

    return {'name': table_name, 'columns': columns, 'idMethod': columns[0].get('idMethod', 'native')}

def map_java_to_sql(java_type):
    mapping = {
        'int': 'INTEGER',
        'Integer': 'INTEGER',
        'long': 'BIGINT',
        'Long': 'BIGINT',
        'String': 'VARCHAR',
        'Date': 'TIMESTAMP',
        'boolean': 'BOOLEAN',
        'Boolean': 'BOOLEAN',
        'double': 'DOUBLE',
        'float': 'FLOAT',
        'BigDecimal': 'DECIMAL'
    }
    return mapping.get(java_type, 'VARCHAR')

def generate_xml(tables):
    root = ET.Element("database")
    root.set("name", "recovered_db")
    root.set("defaultIdMethod", "native")

    for t_name, t_data in tables.items():
        tbl = ET.SubElement(root, "table")
        tbl.set("name", t_name)
        
        # Set table-level idMethod if detected
        if 'idMethod' in t_data and t_data['idMethod'] != 'native':
             tbl.set("idMethod", t_data['idMethod'])

        for col in t_data['columns']:
            c = ET.SubElement(tbl, "column")
            c.set("name", col['name'])
            c.set("type", col['type'])
            if 'primaryKey' in col:
                c.set("primaryKey", "true")
                c.set("required", "true")
                # Deprecated but sometimes useful:
                if t_data.get('idMethod') == 'native' and col['type'] == 'INTEGER':
                     c.set("autoIncrement", "true")

    # Pretty print
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    return xmlstr

if __name__ == "__main__":
    # Point this to your source root
    TARGET_DIR = r"c:\Python" 
    
    tables = analyze_directory(TARGET_DIR)
    xml_output = generate_xml(tables)
    
    output_path = "recovered_schema.xml"
    with open(output_path, "w") as f:
        f.write(xml_output)
    
    print(f"Recovery complete. Schema written to {output_path}")
