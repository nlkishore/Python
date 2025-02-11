import os
import zipfile
import shutil

# Define paths
zip_file = "sample.zip"
extract_dir = "temp_extracted"
target_dir = "final_jars"

# Ensure directories exist
os.makedirs(extract_dir, exist_ok=True)
os.makedirs(target_dir, exist_ok=True)

# Extract ZIP file
with zipfile.ZipFile(zip_file, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

# Process EAR files
for file in os.listdir(extract_dir):
    if file.endswith(".ear"):
        ear_path = os.path.join(extract_dir, file)
        ear_extract_path = os.path.join(extract_dir, file.replace(".ear", "_extracted"))
        os.makedirs(ear_extract_path, exist_ok=True)

        with zipfile.ZipFile(ear_path, 'r') as ear_ref:
            ear_ref.extractall(ear_extract_path)

        # Locate WEB-INF/lib and copy JAR files
        for root, dirs, files in os.walk(ear_extract_path):
            if "WEB-INF/lib" in root.replace("\\", "/"):
                for jar in files:
                    if jar.endswith(".jar"):
                        shutil.copy(os.path.join(root, jar), target_dir)

print("Extraction and copying completed.")
