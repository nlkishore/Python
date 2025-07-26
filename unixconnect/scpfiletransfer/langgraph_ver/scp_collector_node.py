# scp_collector_node.py
import configparser
import subprocess
import os
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def collect_from_host(label, host, user, key_path, remote_file, destination_dir, expected_checksum=None):
    os.makedirs(destination_dir, exist_ok=True)
    filename = os.path.basename(remote_file)
    local_path = os.path.join(destination_dir, f"{label}_{filename}")

    scp_cmd = [
        "scp",
        "-i", key_path,
        f"{user}@{host}:{remote_file}",
        local_path
    ]

    logging.info(f"🔄 [{label}] Fetching {remote_file} from {host}...")
    try:
        subprocess.run(scp_cmd, check=True)
        logging.info(f"✅ [{label}] Stored at {local_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ [{label}] Failed to fetch file: {e}")
        return

    # Checksum validation if provided
    if expected_checksum:
        import hashlib
        def sha256sum(path):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()

        actual = sha256sum(local_path)
        if actual == expected_checksum:
            logging.info(f"🔐 [{label}] Checksum matched.")
        else:
            logging.warning(f"⚠️ [{label}] Checksum mismatch! Expected {expected_checksum}, got {actual}")

def scp_collector_node(state):
    config_path = state["config_file"]
    destination_dir = state["output_dir"]
    max_workers = state.get("max_threads", 4)

    config = configparser.ConfigParser()
    config.read(config_path)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for section in config.sections():
            details = config[section]
            executor.submit(
                collect_from_host,
                label=section,
                host=details["host"],
                user=details["user"],
                key_path=details["key_path"],
                remote_file=details["remote_file"],
                destination_dir=destination_dir,
                expected_checksum=details.get("expected_checksum")
            )

    return {"status": "collection_complete", "output_dir": destination_dir}