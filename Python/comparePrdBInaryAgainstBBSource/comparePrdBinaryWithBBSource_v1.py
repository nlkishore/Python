import os
import zipfile
import hashlib

def compute_jar_content_hash(jar_path):
    """
    Compute a reliable SHA-256 hash for the contents of a JAR file.
    This ignores metadata and normalizes the order of files.
    """
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Collect hashes for all files in the JAR
            hashes = []
            for file_name in sorted(jar.namelist()):  # Sort to ensure consistent order
                with jar.open(file_name) as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes.append(file_hash)
            # Combine hashes into a single hash for the entire JAR
            return hashlib.sha256(''.join(hashes).encode()).hexdigest()
    except Exception as e:
        print(f"Error reading JAR file {jar_path}: {e}")
        return None

def compare_folders(folder1, folder2):
    """
    Compare all JAR files in two folders.
    """
    # Get the list of JAR files in each folder
    jar_files1 = [f for f in os.listdir(folder1) if f.endswith('.jar')]
    jar_files2 = [f for f in os.listdir(folder2) if f.endswith('.jar')]

    # Sort file names to ensure consistent comparison order
    jar_files1.sort()
    jar_files2.sort()

    # Check if the two folders have the same JAR files
    if set(jar_files1) != set(jar_files2):
        print("The folders contain different sets of JAR files.")
        print(f"Files in {folder1} but not in {folder2}: {set(jar_files1) - set(jar_files2)}")
        print(f"Files in {folder2} but not in {folder1}: {set(jar_files2) - set(jar_files1)}")
        return

    # Compare hashes for matching JAR files
    for jar_file in jar_files1:
        jar_path1 = os.path.join(folder1, jar_file)
        jar_path2 = os.path.join(folder2, jar_file)

        hash1 = compute_jar_content_hash(jar_path1)
        hash2 = compute_jar_content_hash(jar_path2)

        if hash1 is None or hash2 is None:
            print(f"Skipping comparison for {jar_file} due to errors.")
            continue

        if hash1 == hash2:
            print(f"{jar_file}: MATCH")
        else:
            print(f"{jar_file}: DIFFER")

# Example usage
folder1 = "path/to/folder1"  # Replace with the actual path
folder2 = "path/to/folder2"  # Replace with the actual path

compare_folders(folder1, folder2)
