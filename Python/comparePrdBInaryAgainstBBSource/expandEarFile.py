import os
import zipfile

def extract_ear_to_webinf(ear_file_path, output_directory):
    """
    Extract the EAR file contents up to the WEB-INF level, including WAR files but without expanding JAR files.

    Parameters:
        ear_file_path (str): Path to the EAR file.
        output_directory (str): Path to the directory where the contents will be extracted.
    """
    if not os.path.exists(ear_file_path):
        print(f"EAR file not found: {ear_file_path}")
        return

    try:
        with zipfile.ZipFile(ear_file_path, 'r') as ear:
            ear_name = os.path.splitext(os.path.basename(ear_file_path))[0]
            ear_output_dir = os.path.join(output_directory, ear_name)
            os.makedirs(ear_output_dir, exist_ok=True)

            for file_name in ear.namelist():
                # Extract EAR level files and WAR files only
                if file_name.endswith('.war'):
                    print(f"Extracting WAR: {file_name}")
                    war_output_dir = os.path.join(ear_output_dir, os.path.splitext(file_name)[0])
                    os.makedirs(war_output_dir, exist_ok=True)
                    extract_war_to_webinf(ear.open(file_name), war_output_dir)
                elif file_name.startswith("META-INF/") or file_name.endswith(".xml"):
                    print(f"Extracting EAR-level file: {file_name}")
                    ear.extract(file_name, ear_output_dir)
    except Exception as e:
        print(f"Error processing EAR file {ear_file_path}: {e}")

def extract_war_to_webinf(war_file, output_directory):
    """
    Extract the WAR file contents up to the WEB-INF level, skipping JAR files inside.

    Parameters:
        war_file (file): File-like object for the WAR file.
        output_directory (str): Path to the directory where the contents will be extracted.
    """
    try:
        with zipfile.ZipFile(war_file, 'r') as war:
            for file_name in war.namelist():
                # Only extract up to WEB-INF level and skip JAR files
                if file_name.startswith(("WEB-INF/", "META-INF/", "config/", "content/")) and not file_name.endswith(".jar"):
                    print(f"Extracting: {file_name}")
                    war.extract(file_name, output_directory)
    except Exception as e:
        print(f"Error processing WAR file: {e}")

def extract_multiple_ears(input_folder, output_directory):
    """
    Extract all EAR files in the specified folder to the output directory.

    Parameters:
        input_folder (str): Path to the folder containing EAR files.
        output_directory (str): Path to the directory where the contents will be extracted.
    """
    if not os.path.exists(input_folder):
        print(f"Input folder does not exist: {input_folder}")
        return

    # Process each EAR file in the input folder
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".ear"):
            print(f"Processing EAR file: {file_name}")
            ear_file_path = os.path.join(input_folder, file_name)
            extract_ear_to_webinf(ear_file_path, output_directory)

# Example usage
input_folder = "path/to/ear_files_folder"  # Replace with the folder containing EAR files
output_directory = "path/to/output/folder"  # Replace with your desired output folder

extract_multiple_ears(input_folder, output_directory)