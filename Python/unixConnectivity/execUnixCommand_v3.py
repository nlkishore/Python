import paramiko
import time
import os
import json
import logging
import configparser
import datetime
from collections import Counter

# Configure logging
LOG_FILE = "ssh_command_history.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Define Unix server details
HOST = "your_unix_server"
PORT = 22
USERNAME = "your_username"
PASSWORD = "your_password"  # Use SSH keys for better security
SUDO_PASSWORD = "your_sudo_password"

# Files for storing history and commands
HISTORY_FILE = "command_history.json"
COMMANDS_FILE = "commands.ini"

def load_commands():
    """Load commands from an INI file."""
    config = configparser.ConfigParser()
    if os.path.exists(COMMANDS_FILE):
        config.read(COMMANDS_FILE)
        if 'Shortcuts' in config:
            return dict(config['Shortcuts'])
    return {}

def load_history():
    """Load command history from a JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return Counter(json.load(file))
    return Counter()

def save_history(history):
    """Save command history to a JSON file."""
    with open(HISTORY_FILE, "w") as file:
        json.dump(dict(history), file)

def ssh_connect():
    """Establish an SSH connection with sudo capability."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD, timeout=10)
        return client
    except Exception as e:
        print(f"Error connecting to {HOST}: {e}")
        return None

def execute_command(client, command):
    """Execute a command with sudo and return the output."""
    try:
        shell = client.invoke_shell()
        shell.send(f"sudo -S -p '' {command}\n")
        time.sleep(1)
        shell.send(SUDO_PASSWORD + "\n")
        time.sleep(2)

        output = ""
        while shell.recv_ready():
            output += shell.recv(1024).decode()

        return output
    except Exception as e:
        return f"Error executing command: {e}"

def get_log_entries(client, log_file, start_time, search_string):
    """Fetch log entries between start and end time and extract relevant lines."""
    # Convert start time to datetime object
    start_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    end_dt = start_dt + datetime.timedelta(minutes=10)  # 10-minute window

    # Format timestamps for grep
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Construct grep command
    log_command = f"sudo awk '$0 >= \"{start_str}\" && $0 <= \"{end_str}\"' {log_file}"
    print(f"\nFetching logs from {start_str} to {end_str}...\n")
    
    log_output = execute_command(client, log_command)
    
    if "Error" in log_output:
        print("Error retrieving log data.")
        return

    log_lines = log_output.split("\n")
    first_occurrence = None
    last_occurrence = None

    # Find first and last occurrence of the search string
    for i, line in enumerate(log_lines):
        if search_string in line:
            if first_occurrence is None:
                first_occurrence = i
            last_occurrence = i

    if first_occurrence is not None and last_occurrence is not None:
        extracted_logs = log_lines[first_occurrence:last_occurrence + 1]
        print("\nExtracted Log Data:\n" + "\n".join(extracted_logs))
    else:
        print("\nNo occurrences of the search string found in the log file.")

def main():
    """Main function to handle user input and execute commands."""
    client = ssh_connect()
    if not client:
        return

    commands = load_commands()
    history = load_history()

    print("\nConnected to Unix Server. Use shortcuts for quick execution.")
    print("Available shortcuts:", ", ".join(commands.keys()))
    
    while True:
        # Show top 3 frequently used commands
        if history:
            print("\nMost used commands:", ", ".join([cmd for cmd, _ in history.most_common(3)]))

        cmd = input("\nEnter shortcut or command (or 'logs' for log retrieval, 'exit' to quit): ").strip().lower()
        
        if cmd == "exit":
            print("Closing connection...")
            save_history(history)
            client.close()
            break
        
        elif cmd == "logs":
            log_file = input("Enter log file path (e.g., /var/log/syslog): ").strip()
            start_time = input("Enter start time (YYYY-MM-DD HH:MM:SS): ").strip()
            search_string = input("Enter search string: ").strip()

            get_log_entries(client, log_file, start_time, search_string)
            continue

        command = commands.get(cmd, cmd)  # Use shortcut or raw command

        print(f"\nExecuting: {command}\n")
        output = execute_command(client, command)
        print(output)

        # Log the command execution
        logging.info(f"Executed command: {command}")
        
        # Update command history
        history[command] += 1

if __name__ == "__main__":
    main()
