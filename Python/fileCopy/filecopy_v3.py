import os
import shutil

def copy_java_files(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".java"):
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_dir, os.path.relpath(src_file_path, src_dir))
                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                shutil.copy2(src_file_path, dest_file_path)
                print(f"Copied {src_file_path} to {dest_file_path}")

# Example usage
source_directory = 'path_to_source_directory'
destination_directory = 'path_to_destination_directory'
copy_java_files(source_directory, destination_directory)
