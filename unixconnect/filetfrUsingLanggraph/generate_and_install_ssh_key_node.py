import subprocess
import paramiko
import os
import logging

def generate_and_install_ssh_key_node(state):
    username = state["username"]
    server = state["host"]
    remote_password = state["password"]  # Needed for initial setup
    key_dir = state.get("key_dir", os.path.expanduser("~/.ssh"))
    key_name = f"{username}_id_rsa"
    key_path = os.path.join(key_dir, key_name)

    os.makedirs(key_dir, exist_ok=True)

    # Step 1: Generate SSH key
    if not os.path.exists(key_path):
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096",
            "-C", f"{username}@{server}",
            "-f", key_path,
            "-N", ""
        ], check=True)
        logging.info(f"🔑 Generated SSH key at: {key_path}")
    else:
        logging.info(f"🔑 Reusing existing SSH key: {key_path}")

    # Step 2: Install public key on remote server
    pub_key = open(f"{key_path}.pub", "r").read().strip()

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, username=username, password=remote_password)

        cmds = [
            'mkdir -p ~/.ssh',
            f'echo "{pub_key}" >> ~/.ssh/authorized_keys',
            'chmod 700 ~/.ssh',
            'chmod 600 ~/.ssh/authorized_keys'
        ]
        for cmd in cmds:
            stdin, stdout, stderr = client.exec_command(cmd)
            err = stderr.read().decode()
            if err:
                raise RuntimeError(f"Failed to run: {cmd}\n{err}")
        logging.info("✅ SSH key installed on remote server.")
    finally:
        client.close()

    return {
        "status": "installed",
        "key_path": key_path,
        "public_key": pub_key
    }