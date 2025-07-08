import paramiko
import configparser
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_credentials(config_path, section):
    config = configparser.ConfigParser()
    config.read(config_path)
    return {
        "host": config[section]["host"],
        "username": config[section]["user"],
        "key_path": config[section]["key_path"]
    }

def ssh_connect(creds):
    try:
        key = paramiko.RSAKey.from_private_key_file(creds["key_path"])
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=creds["host"], username=creds["username"], pkey=key)
        return client
    except Exception as e:
        logging.error(f"SSH connection failed: {e}")
        raise

def run_cmd(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        logging.error(f"Command failed: {command}\n{err}")
        raise RuntimeError(err)
    return out.strip()

def cleanup_tmp_file(client, filepath):
    try:
        run_cmd(client, f"rm -f {filepath}")
        logging.info(f"Cleaned up {filepath}")
    except Exception as e:
        logging.warning(f"Failed to clean up {filepath}: {e}")

def owner_copy_workflow(config_file, owner1, owner2, source_file, destination_path):
    tmp_file = f"/tmp/{os.path.basename(source_file)}"

    # Phase 1: Owner1 to /tmp
    creds1 = load_credentials(config_file, owner1)
    logging.info(f"Connecting as {owner1}")
    ssh1 = ssh_connect(creds1)
    try:
        run_cmd(ssh1, f"cp {source_file} {tmp_file}")
        logging.info(f"{owner1}: copied file to {tmp_file}")
    finally:
        ssh1.close()

    # Phase 2: /tmp to destination as Owner2
    creds2 = load_credentials(config_file, owner2)
    logging.info(f"Connecting as {owner2}")
    ssh2 = ssh_connect(creds2)
    try:
        run_cmd(ssh2, f"cp {tmp_file} {destination_path}")
        logging.info(f"{owner2}: copied file to destination {destination_path}")
        cleanup_tmp_file(ssh2, tmp_file)
    finally:
        ssh2.close()