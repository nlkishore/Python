import configparser
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def collect_files(config_path, destination_dir):
    config = configparser.ConfigParser()
    config.read(config_path)

    os.makedirs(destination_dir, exist_ok=True)

    for section in config.sections():
        host = config[section]["host"]
        user = config[section]["user"]
        key_path = config[section]["key_path"]
        remote_file = config[section]["remote_file"]
        filename = os.path.basename(remote_file)
        local_path = os.path.join(destination_dir, f"{section}_{filename}")

        scp_cmd = [
            "scp",
            "-i", key_path,
            f"{user}@{host}:{remote_file}",
            local_path
        ]

        logging.info(f"📦 Fetching from {section} ({host})...")
        try:
            subprocess.run(scp_cmd, check=True)
            logging.info(f"✅ Saved to {local_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Failed to fetch from {section}: {e}")

if __name__ == "__main__":
    collect_files(config_path="servers.ini", destination_dir="/home/collector/received_files")