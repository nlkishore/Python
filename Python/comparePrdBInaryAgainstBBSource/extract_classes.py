import zipfile
import os
import shutil

def extract_specific_classes(jar_path, output_dir, class_names):
    """
    Extracts specific .class files from a JAR while preserving the folder structure.
    
    :param jar_path: Path to the JAR file.
    :param output_dir: Directory where extracted files will be stored.
    :param class_names: List of class files to extract (e.g., ["com/example/MyClass.class"])
    """
    if not os.path.exists(jar_path):
        print(f"Error: JAR file '{jar_path}' not found!")
        return
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with zipfile.ZipFile(jar_path, 'r') as jar:
        for class_file in class_names:
            if class_file in jar.namelist():
                dest_file_path = os.path.join(output_dir, class_file)
                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                
                # Extract and copy to the new folder
                with jar.open(class_file) as source, open(dest_file_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                print(f"Extracted: {class_file} -> {dest_file_path}")
            else:
                print(f"Warning: {class_file} not found in the JAR!")

# Example Usage
if __name__ == "__main__":
    jar_file = "example.jar"  # Path to your JAR file
    output_folder = "extracted_classes"  # Destination folder
    classes_to_extract = [
        "com/example/MyClass.class",
        "org/example/Helper.class"
    ]

    extract_specific_classes(jar_file, output_folder, classes_to_extract)
