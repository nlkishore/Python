import os
import shutil

def create_folder_structure_and_copy_file(src_file, dest_root):
    with open(src_file, 'r') as file:
        lines = file.readlines()
    
    package_line = next((line for line in lines if line.startswith('package ')), None)
    
    if package_line:
        package_path = package_line.split().rstrip(';').replace('.', os.sep)
        dest_dir = os.path.join(dest_root, package_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_file = os.path.join(dest_dir, os.path.basename(src_file))
        shutil.copy2(src_file, dest_file)
        print(f"Copied {src_file} to {dest_file}")
    else:
        print(f"No package declaration found in {src_file}")

# Example usage
source_file = 'path_to_your_java_file.java'
destination_root = 'path_to_destination_root'
create_folder_structure_and_copy_file(source_file, destination_root)