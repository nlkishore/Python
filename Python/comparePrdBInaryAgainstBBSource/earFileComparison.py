import zipfile
import hashlib
import os
import shutil

def hash_file(file_path):
    """Generate SHA-256 hash of the file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_ear(ear_file, extract_to):
    """Extract EAR file to the specified directory."""
    with zipfile.ZipFile(ear_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def compare_files(file1, file2):
    """Compare two files using their SHA-256 hash."""
    return hash_file(file1) == hash_file(file2)

def find_differences(dir1, dir2, diff_dir1, diff_dir2):
    """Find differences between two directories and extract different files to separate folders."""
    for root, _, files in os.walk(dir1):
        for file in files:
            file1 = os.path.join(root, file)
            file2 = os.path.join(dir2, os.path.relpath(file1, dir1))
            if not os.path.exists(file2) or not compare_files(file1, file2):
                diff_file1 = os.path.join(diff_dir1, os.path.relpath(file1, dir1))
                diff_file2 = os.path.join(diff_dir2, os.path.relpath(file1, dir1))
                os.makedirs(os.path.dirname(diff_file1), exist_ok=True)
                os.makedirs(os.path.dirname(diff_file2), exist_ok=True)
                shutil.copy2(file1, diff_file1)
                if os.path.exists(file2):
                    shutil.copy2(file2, diff_file2)

# Paths to the EAR files
ear_file1 = 'path/to/earfile1.ear'
ear_file2 = 'path/to/earfile2.ear'

# Directories to extract the EAR files
extract_dir1 = 'extracted_ear1'
extract_dir2 = 'extracted_ear2'

# Directories to store the different files
diff_dir1 = 'differences_ear1'
diff_dir2 = 'differences_ear2'

# Extract the EAR files
extract_ear(ear_file1, extract_dir1)
extract_ear(ear_file2, extract_dir2)

# Find and extract the different files
find_differences(extract_dir1, extract_dir2, diff_dir1, diff_dir2)

print("Comparison and extraction of different files completed.")



Case 2.


import zipfile
import hashlib
import os
import shutil

def hash_file(file_path):
    """Generate SHA-256 hash of the file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_ear(ear_file, extract_to):
    """Extract EAR file to the specified directory."""
    with zipfile.ZipFile(ear_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def compare_files(file1, file2):
    """Compare two files using their SHA-256 hash."""
    return hash_file(file1) == hash_file(file2)

def compare_file_contents(file1, file2):
    """Compare file contents line by line, ignoring spaces and line breaks."""
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = [line.strip() for line in f1 if line.strip()]
        lines2 = [line.strip() for line in f2 if line.strip()]
        return lines1 == lines2

def find_differences(dir1, dir2, diff_dir1, diff_dir2):
    """Find differences between two directories and extract different files to separate folders."""
    for root, _, files in os.walk(dir1):
        for file in files:
            file1 = os.path.join(root, file)
            file2 = os.path.join(dir2, os.path.relpath(file1, dir1))
            if not os.path.exists(file2) or not compare_files(file1, file2):
                if os.path.exists(file2) and compare_file_contents(file1, file2):
                    continue  # Skip files with differences that are only spaces or line breaks
                diff_file1 = os.path.join(diff_dir1, os.path.relpath(file1, dir1))
                diff_file2 = os.path.join(diff_dir2, os.path.relpath(file1, dir1))
                os.makedirs(os.path.dirname(diff_file1), exist_ok=True)
                os.makedirs(os.path.dirname(diff_file2), exist_ok=True)
                shutil.copy2(file1, diff_file1)
                if os.path.exists(file2):
                    shutil.copy2(file2, diff_file2)

# Paths to the EAR files
ear_file1 = 'path/to/earfile1.ear'
ear_file2 = 'path/to/earfile2.ear'

# Directories to extract the EAR files
extract_dir1 = 'extracted_ear1'
extract_dir2 = 'extracted_ear2'

# Directories to store the different files
diff_dir1 = 'differences_ear1'
diff_dir2 = 'differences_ear2'

# Extract the EAR files
extract_ear(ear_file1, extract_dir1)
extract_ear(ear_file2, extract_dir2)

# Find and extract the different files
find_differences(extract_dir1, extract_dir2, diff_dir1, diff_dir2)

print("Comparison and extraction of different files completed.")

