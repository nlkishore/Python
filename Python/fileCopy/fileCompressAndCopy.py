import configparser
import tarfile
import os
import subprocess

def read_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config['Folders']['source_folder'], config['Folders']['destination_folder']

def create_tar_archive(source, tar_path):
    with tarfile.open(tar_path, "w") as tar:
        tar.add(source, arcname=os.path.basename(source))

def compress_file(file_path):
    command = f'compact /c "{file_path}"'
    subprocess.run(command, shell=True, check=True)

if __name__ == "__main__":
    config_file = 'config.ini'
    source_folder, destination_folder = read_config(config_file)
    
    # Create tar archive
    tar_path = os.path.join(destination_folder, 'archive.tar')
    create_tar_archive(source_folder, tar_path)
    
    # Compress the tar archive
    compress_file(tar_path)
    
    print("Files archived and compressed successfully.")
