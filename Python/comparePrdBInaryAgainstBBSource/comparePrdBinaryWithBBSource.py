import os
import hashlib
import zipfile
from pathlib import Path
from filecmp import dircmp

def extract_jar(jar_path, extract_to):
    """Extracts a JAR file to a directory."""
    with zipfile.ZipFile(jar_path, 'r') as jar:
        jar.extractall(extract_to)

def compute_hash(file_path):
    """Computes the SHA-256 hash of a file."""
    hash_func = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def hash_directory(directory):
    """Computes hashes for all files in a directory."""
    file_hashes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)
            file_hashes[relative_path] = compute_hash(file_path)
    return file_hashes

def compare_hashes(hash1, hash2):
    """Compares two hash dictionaries and reports differences."""
    all_files = set(hash1.keys()).union(set(hash2.keys()))
    differences = []
    for file in all_files:
        if hash1.get(file) != hash2.get(file):
            differences.append(file)
    return differences

# Paths to the JAR files and temporary directories
prod_jar = "path/to/production.jar"
source_jar = "path/to/source.jar"
prod_extract_dir = "temp/production"
source_extract_dir = "temp/source"

# Ensure extraction directories exist
Path(prod_extract_dir).mkdir(parents=True, exist_ok=True)
Path(source_extract_dir).mkdir(parents=True, exist_ok=True)

# Extract JARs
extract_jar(prod_jar, prod_extract_dir)
extract_jar(source_jar, source_extract_dir)

# Compute hashes
prod_hashes = hash_directory(prod_extract_dir)
source_hashes = hash_directory(source_extract_dir)

# Compare hashes
differences = compare_hashes(prod_hashes, source_hashes)

# Report results
if differences:
    print("Differences found in the following files:")
    for diff in differences:
        print(diff)
else:
    print("No differences found. The JARs are identical.")
