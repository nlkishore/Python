import paramiko
import configparser
import os

CONFIG_FILE = "servers.ini"

# Load server and command configurations
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

SERVERS = {section: dict(config[section]) for section in config.sections() if section.startswith("server_")}
COMMANDS = {section: dict(config[section]) for section in config.sections() if section.startswith("commands_")}

current_server = None


def connect_to_server(server_config):
    """Establish an SSH connection to the Unix server."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server_config["host"],
            port=int(server_config["port"]),
            username=server_config["username"],
            password=server_config["password"]  # Use SSH key authentication if preferred
        )
        return ssh
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


def execute_command(server_config, command_key):
    """Execute a predefined command on the remote server."""
    if command_key not in COMMANDS[current_server]:
        print(f"⚠️ Command '{command_key}' not found for {current_server}!")
        return

    command = COMMANDS[current_server][command_key]
    ssh = connect_to_server(server_config)
    if not ssh:
        return

    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            print(f"\n✅ Output:\n{output}")
        if error:
            print(f"\n❌ Error:\n{error}")

    finally:
        ssh.close()


def transfer_file(server_config, local_path, remote_path, upload=True):
    """Transfer files using SCP (upload/download)."""
    ssh = connect_to_server(server_config)
    if not ssh:
        return

    try:
        sftp = ssh.open_sftp()
        if upload:
            sftp.put(local_path, remote_path)
            print(f"✅ Uploaded {local_path} to {remote_path}")
        else:
            sftp.get(remote_path, local_path)
            print(f"✅ Downloaded {remote_path} to {local_path}")

    except Exception as e:
        print(f"❌ SCP transfer failed: {e}")

    finally:
        sftp.close()
        ssh.close()


def main():
    """Main function to handle user interaction."""
    global current_server

    print("\n🌍 Multi-Country Unix Automation Tool (SG, MY, OV, HK, ID, TH, CN)\n")
    print("Available servers:", ", ".join(SERVERS.keys()))

    while True:
        cmd = input("\nEnter command (or 'switch <country>', 'run <command>', 'upload <local> <remote>', 'download <remote> <local>', 'exit'): ").strip().lower()

        if cmd == "exit":
            print("Exiting...")
            break

        elif cmd.startswith("switch "):
            country = cmd.split(" ")[1]
            if country in SERVERS:
                current_server = country
                print(f"✅ Switched to {current_server.upper()} server: {SERVERS[current_server]['host']}")
            else:
                print(f"❌ Invalid country! Available: {', '.join(SERVERS.keys())}")

        elif cmd.startswith("run "):
            if not current_server:
                print("⚠️ No server selected! Use 'switch <country>' first.")
                continue

            command_key = cmd.split(" ")[1]
            execute_command(SERVERS[current_server], command_key)

        elif cmd.startswith("upload ") or cmd.startswith("download "):
            if not current_server:
                print("⚠️ No server selected! Use 'switch <country>' first.")
                continue

            parts = cmd.split(" ")
            if len(parts) != 3:
                print("⚠️ Invalid SCP command! Use 'upload <local> <remote>' or 'download <remote> <local>'")
                continue

            action, local_path, remote_path = parts
            upload = action == "upload"
            transfer_file(SERVERS[current_server], local_path, remote_path, upload)

        else:
            print("⚠️ Invalid command! Use 'switch <country>', 'run <command>', 'upload <local> <remote>', 'download <remote> <local>'.")


if __name__ == "__main__":
    main()
