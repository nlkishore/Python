import configparser
import subprocess
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Read configuration
config = configparser.ConfigParser()
config.read("config.ini")

# Get settings
use_robocopy = config.getboolean("General", "use_robocopy")
use_7zip = config.getboolean("General", "use_7zip")
zip_exe_path = config.get("General", "7zip_path").strip('"')

# Get folder mappings
folders = {key: value.split("|") for key, value in config["Folders"].items()}

def copy_with_robocopy(source, destination):
    """Copy files using Robocopy with multithreading"""
    robocopy_cmd = ["robocopy", source, destination, "/E", "/MT:32"]
    logging.info(f"Executing: {' '.join(robocopy_cmd)}")
    subprocess.run(robocopy_cmd, shell=True)

def copy_with_7zip(source, destination):
    """Compress source using 7-Zip, then extract at destination"""
    archive_path = os.path.join(destination, "backup.7z")
    
    # Compress source folder
    compress_cmd = [zip_exe_path, "a", "-t7z", archive_path, source]
    logging.info(f"Executing: {' '.join(compress_cmd)}")
    subprocess.run(compress_cmd, shell=True)

    # Extract in destination
    extract_cmd = [zip_exe_path, "x", archive_path, f"-o{destination}", "-y"]
    logging.info(f"Executing: {' '.join(extract_cmd)}")
    subprocess.run(extract_cmd, shell=True)

    # Delete archive after extraction
    os.remove(archive_path)

# Process each folder
for key, (src, dest) in folders.items():
    if not os.path.exists(src):
        logging.warning(f"Source folder does not exist: {src}")
        continue
    if not os.path.exists(dest):
        os.makedirs(dest)

    logging.info(f"Copying {src} to {dest}...")

    if use_robocopy:
        copy_with_robocopy(src, dest)
    elif use_7zip:
        copy_with_7zip(src, dest)
    else:
        logging.error("No valid copy method enabled in config.")

logging.info("Copy process completed!")
