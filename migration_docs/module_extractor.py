import os
import shutil
import re

# Module Extractor
# Moves Java files into separate Maven-style sub-modules based on their imports.
# Useful for isolating legacy code (Village, Torque) from the main codebase.

def extract_modules(source_root, target_root, dry_run=True):
    # Rules: (Priority Order)
    # If a file matches multiple, first one wins.
    rules = [
        {
            "name": "legacy-village",
            "pattern": re.compile(r"import\s+com\.workingdogs\.village"),
            "description": "Code using Legacy Village Library"
        },
        {
            "name": "legacy-torque",
            "pattern": re.compile(r"import\s+org\.apache\.torque"),
            "description": "Code using Legacy Torque ORM"
        }
    ]

    print(f"Scanning {source_root}...")
    print(f"Target Root: {target_root}")
    print(f"Dry Run: {dry_run}")

    stats = {r['name']: 0 for r in rules}

    for root, dirs, files in os.walk(source_root):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                
                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

                # Check rules
                matched_module = None
                for rule in rules:
                    if rule["pattern"].search(content):
                        matched_module = rule["name"]
                        break
                
                if matched_module:
                    # Calculate relative path to maintain package structure
                    # e.g. c:/project/src/com/foo/Bar.java -> com/foo/Bar.java
                    # Assumption: source_root points to the root of the source tree (e.g. src/main/java)
                    # If source_root is just the project root, we need to be careful.
                    
                    rel_path = os.path.relpath(file_path, source_root)
                    
                    # Target structure: target_root / module_name / src / main / java / rel_path
                    target_path = os.path.join(target_root, matched_module, "src", "main", "java", rel_path)
                    
                    if dry_run:
                        print(f"[DRY-RUN] Move {file} -> {matched_module}")
                    else:
                        print(f"[MOVE] {file} -> {target_path}")
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.move(file_path, target_path)
                    
                    stats[matched_module] += 1

    print("-" * 30)
    print("Extraction Summary:")
    for module, count in stats.items():
        print(f"  {module}: {count} files")

if __name__ == "__main__":
    # CONFIGURATION
    # 1. Source Directory (e.g., c:\myproject\src\main\java)
    SOURCE_DIR = r"c:\Python\Java-Projects" 
    
    # 2. Output Directory for new modules
    OUTPUT_DIR = r"c:\Python\extracted_modules"
    
    # 3. Set to False to actually move files
    DRY_RUN = True
    
    extract_modules(SOURCE_DIR, OUTPUT_DIR, DRY_RUN)
