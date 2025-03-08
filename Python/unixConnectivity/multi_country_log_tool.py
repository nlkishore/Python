import paramiko
import configparser
import threading
import os
import json
import datetime

CONFIG_FILE = "servers.ini"
HISTORY_FILE = "command_history.json"

# Load configurations
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

COUNTRY_SERVERS = {section: dict(config[section]) for section in config.sections() if section.startswith("server_")}
COMMANDS = dict(config["Commands"]) if "Commands" in config else {}

current_server = None


def ssh_connect(host, username, key_path):
    """Establish an SSH connection using a private key."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey(filename=os.path.expanduser(key_path))
        client.connect(hostname=host, username=username, pkey=key, timeout=10)
        return client
    except Exception as e:
        print(f"Error connecting to {host}: {e}")
        return None


def execute_remote_command(server, command):
    """Execute command on a remote server."""
    host, username, key_path = server["host"], server["username"], server["key_path"]
    client = ssh_connect(host, username, key_path)
    if not client:
        return f"Failed to connect to {host}"

    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()

    client.close()
    
    return output if output else error


def parallel_execution(command):
    """Execute a command on all servers in parallel."""
    threads = []
    results = {}

    def run_on_server(country, server):
        results[country] = execute_remote_command(server, command)

    for country, server in COUNTRY_SERVERS.items():
        thread = threading.Thread(target=run_on_server, args=(country, server))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return results


def save_history(command):
    """Save executed command history."""
    history = load_history()
    history.append({"timestamp": str(datetime.datetime.now()), "command": command})
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file)


def load_history():
    """Load command history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    return []


def execute_predefined_commands():
    """Execute all predefined commands from the INI file across servers."""
    for cmd_name, command in COMMANDS.items():
        print(f"\nExecuting command: {cmd_name} -> {command}\n")
        results = parallel_execution(command)
        
        for country, output in results.items():
            print(f"\n📌 Output from {country.upper()} Server:")
            print(output if output else "No output received.")

        save_history(command)


def main():
    """Main function to handle execution."""
    global current_server

    print("\n🌍 Multi-Country Log Analysis Tool\n")
    print("Available countries:", ", ".join(COUNTRY_SERVERS.keys()))
    
    # Automatically execute predefined commands from INI file
    execute_predefined_commands()


if __name__ == "__main__":
    main()
