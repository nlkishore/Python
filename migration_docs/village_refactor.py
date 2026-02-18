import os
import re

# Logic to refactor com.workingdogs.village usage
# This script scans Java files and performs the following:
# 1. Replaces imports of com.workingdogs.village.* with a custom Adapter package.
# 2. Replaces usage of Village classes (Record, Value, Schema) with Adapter classes.
# 3. Creates a report of modified files.

def scan_and_refactor(directory, dry_run=True):
    # Setup patterns
    import_pattern = re.compile(r"import\s+com\.workingdogs\.village\.(.*);")
    usage_pattern = re.compile(r"\bcom\.workingdogs\.village\.")
    
    # Adapter package (User to configure)
    ADAPTER_PACKAGE = "com.mycompany.legacy.adapter.village"
    
    files_modified = 0
    
    print(f"Scanning {directory} for Village usage (Dry Run: {dry_run})...")

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    original_content = f.read()

                new_content = original_content
                modified = False

                # 1. Replace Imports
                if import_pattern.search(new_content):
                    new_content = import_pattern.sub(f"import {ADAPTER_PACKAGE}.\\1;", new_content)
                    modified = True

                # 2. Replace fully qualified usage
                if usage_pattern.search(new_content):
                    new_content = usage_pattern.sub(f"{ADAPTER_PACKAGE}.", new_content)
                    modified = True

                if modified:
                    print(f"Refactoring candidate: {file}")
                    if not dry_run:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                    log_refactor_candidate(path)
                    files_modified += 1

    print(f"Total files identifying for refactoring: {files_modified}")

def log_refactor_candidate(file_path):
    with open("village_refactor_report.txt", "a") as report:
        report.write(f"{file_path}\n")

if __name__ == "__main__":
    # Example usage: point to the source root
    target_dir = r"c:\Python\Java-Projects" # Update this path to your Java source
    # Set dry_run=False to apply changes
    scan_and_refactor(target_dir, dry_run=True)
    print("Scan complete. See village_refactor_report.txt")
