import paramiko
import os
import logging

def connect_with_key(host, username, key_path):
    key = paramiko.RSAKey.from_private_key_file(key_path)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=username, pkey=key)
    return ssh

def run_ssh_command(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    err = stderr.read().decode()
    if err:
        raise RuntimeError(f"SSH command failed: {cmd}\nError: {err}")

def owner_copy_workflow_node(state):
    host = state["host"]
    owner1 = state["owner1"]
    owner2 = state["owner2"]
    key_path1 = state["key_path_owner1"]
    key_path2 = state["key_path_owner2"]
    source_file = state["source_file"]
    destination_path = state["destination_path"]

    filename = os.path.basename(source_file)
    tmp_path = f"/tmp/{filename}"

    logging.info(f"🔁 Beginning file transfer via {host}")

    # Step 1: owner1 → /tmp
    ssh1 = connect_with_key(host, owner1, key_path1)
    try:
        run_ssh_command(ssh1, f"cp {source_file} {tmp_path}")
        logging.info(f"✅ {owner1} copied to {tmp_path}")
    finally:
        ssh1.close()

    # Step 2: /tmp → destination as owner2
    ssh2 = connect_with_key(host, owner2, key_path2)
    try:
        run_ssh_command(ssh2, f"cp {tmp_path} {destination_path}")
        logging.info(f"✅ {owner2} copied to {destination_path}")

        # Cleanup
        run_ssh_command(ssh2, f"rm -f {tmp_path}")
        logging.info(f"🧹 Cleaned up {tmp_path}")
    finally:
        ssh2.close()

    return {
        "status": "success",
        "tmp_file": tmp_path,
        "final_path": os.path.join(destination_path, filename)
    }