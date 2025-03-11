import configparser
import subprocess
import logging
import os
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Read configuration
config = configparser.ConfigParser()
config.read("config.ini")

# Get settings
use_robocopy = config.getboolean("General", "use_robocopy")
use_7zip = config.getboolean("General", "use_7zip")
use_tar = config.getboolean("General", "use_tar")
use_compact = config.getboolean("General", "use_compact")
compress_before_transfer = config.getboolean("General", "compress_before_transfer")
zip_exe_path = config.get("General", "7zip_path").strip('"')
tar_exe_path = config.get("General", "tar_exe_path").strip('"')

# Get folder mappings
folders = {key: value.split("|") for key, value in config["Folders"].items()}

def compress_with_7zip(source, destination):
    """Compress source using 7-Zip before transfer"""
    archive_path = os.path.join(destination, "backup.7z")
    compress_cmd = [zip_exe_path, "a", "-t7z", archive_path, source]
    
    logging.info(f"Compressing with 7-Zip: {' '.join(compress_cmd)}")
    subprocess.run(compress_cmd, shell=True)

    return archive_path

def decompress_with_7zip(archive_path, destination):
    """Extract compressed 7-Zip file after transfer"""
    extract_cmd = [zip_exe_path, "x", archive_path, f"-o{destination}", "-y"]
    
    logging.info(f"Extracting with 7-Zip: {' '.join(extract_cmd)}")
    subprocess.run(extract_cmd, shell=True)

    os.remove(archive_path)

def compress_with_tar(source, destination):
    """Compress source using tar before transfer"""
    archive_path = os.path.join(destination, "backup.tar.gz")
    compress_cmd = [tar_exe_path, "-czf", archive_path, "-C", os.path.dirname(source), os.path.basename(source)]
    
    logging.info(f"Compressing with tar: {' '.join(compress_cmd)}")
    subprocess.run(compress_cmd, shell=True)

    return archive_path

def decompress_with_tar(archive_path, destination):
    """Extract tar archive after transfer"""
    extract_cmd = [tar_exe_path, "-xzf", archive_path, "-C", destination]
    
    logging.info(f"Extracting with tar: {' '.join(extract_cmd)}")
    subprocess.run(extract_cmd, shell=True)

    os.remove(archive_path)

def compress_with_compact(source):
    """Compress folder using Windows Compact.exe (NTFS compression)"""
    compress_cmd = ["compact", "/C", "/S", source]
    
    logging.info(f"Compressing with Compact.exe: {' '.join(compress_cmd)}")
    subprocess.run(compress_cmd, shell=True)

def decompress_with_compact(destination):
    """Decompress folder using Windows Compact.exe"""
    decompress_cmd = ["compact", "/U", "/S", destination]
    
    logging.info(f"Decompressing with Compact.exe: {' '.join(decompress_cmd)}")
    subprocess.run(decompress_cmd, shell=True)

def copy_with_robocopy(source, destination):
    """Copy files using Robocopy with multithreading"""
    robocopy_cmd = ["robocopy", source, destination, "/E", "/MT:32"]
    logging.info(f"Executing: {' '.join(robocopy_cmd)}")
    subprocess.run(robocopy_cmd, shell=True)

def copy_with_shutil(source, destination):
    """Fallback method: Copy using shutil (Python built-in)"""
    logging.info(f"Copying using shutil from {source} to {destination}")
    shutil.copytree(source, destination, dirs_exist_ok=True)

# Process each folder
for key, (src, dest) in folders.items():
    if not os.path.exists(src):
        logging.warning(f"Source folder does not exist: {src}")
        continue
    if not os.path.exists(dest):
        os.makedirs(dest)

    logging.info(f"Copying {src} to {dest}...")

    archive_path = None

    # Compress files before copying if enabled
    if compress_before_transfer:
        if use_7zip:
            archive_path = compress_with_7zip(src, dest)
        elif use_tar:
            archive_path = compress_with_tar(src, dest)
        elif use_compact:
            compress_with_compact(src)

    # Copy data
    if archive_path:
        if use_robocopy:
            copy_with_robocopy(archive_path, dest)
        else:
            copy_with_shutil(archive_path, dest)

        # Decompress after transfer
        if use_7zip:
            decompress_with_7zip(archive_path, dest)
        elif use_tar:
            decompress_with_tar(archive_path, dest)
    else:
        if use_robocopy:
            copy_with_robocopy(src, dest)
        else:
            copy_with_shutil(src, dest)

        if use_compact:
            decompress_with_compact(dest)

logging.info("Copy process completed!")
