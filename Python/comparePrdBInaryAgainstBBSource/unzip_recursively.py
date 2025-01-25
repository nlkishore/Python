import os
import zipfile

def unzip_recursively(zip_file_path, output_directory=None):
    """
    Recursively unzips a ZIP file, including nested ZIP files.

    Parameters:
        zip_file_path (str): Path to the ZIP file.
        output_directory (str): Path to the directory where the ZIP contents will be extracted.
                                If None, the folder will be created with the same name as the ZIP file.
    """
    if not os.path.exists(zip_file_path):
        print(f"ZIP file not found: {zip_file_path}")
        return

    # Determine output folder if not provided
    if output_directory is None:
        zip_dir, zip_name = os.path.split(zip_file_path)
        folder_name = os.path.splitext(zip_name)[0]
        output_directory = os.path.join(zip_dir, folder_name)

    os.makedirs(output_directory, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Extract the contents of the ZIP file
            zip_ref.extractall(output_directory)
            print(f"Extracted: {zip_file_path} -> {output_directory}")

            # Process each item in the ZIP file
            for item in zip_ref.namelist():
                item_path = os.path.join(output_directory, item)

                if item.endswith(".zip"):  # Check if the item is a ZIP file
                    print(f"Found nested ZIP file: {item_path}")
                    # Recursively unzip the nested ZIP file
                    nested_output_dir = os.path.join(output_directory, os.path.splitext(item)[0])
                    unzip_recursively(item_path, nested_output_dir)
                elif os.path.isdir(item_path):
                    print(f"Folder: {item}")
                elif os.path.isfile(item_path):
                    print(f"File: {item}")
                else:
                    print(f"Unknown type: {item}")
    except Exception as e:
        print(f"Error while unzipping: {e}")

# Example usage
zip_file_path = "path/to/your/outer_zip_file.zip"  # Replace with the actual ZIP file path
unzip_recursively(zip_file_path)
