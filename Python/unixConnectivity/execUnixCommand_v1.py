import paramiko
import time
import os
import json
import logging
from collections import Counter

# Configure logging
LOG_FILE = "ssh_command_history.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Define the Unix server details
HOST = "your_unix_server"
PORT = 22
USERNAME = "your_username"
PASSWORD = "your_password"  # Use SSH keys for better security
SUDO_PASSWORD = "your_sudo_password"

# Command history storage
HISTORY_FILE = "command_history.json"

# Predefined command shortcuts
COMMANDS = {
    "disk": "df -h",
    "mem": "free -m",
    "cpu": "top -bn1 | head -n 10",
    "logs": "sudo tail -f /var/log/syslog",
    "users": "who",
    "uptime": "uptime",
    "processes": "ps aux --sort=-%cpu | head -10",
}

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
        shell.send("sudo -S -p '' {}\n".format(command))
        time.sleep(1)
        shell.send(SUDO_PASSWORD + "\n")
        time.sleep(2)

        output = ""
        while shell.recv_ready():
            output += shell.recv(1024).decode()

        return output
    except Exception as e:
        return f"Error executing command: {e}"

def main():
    """Main function to handle user input and execute commands."""
    client = ssh_connect()
    if not client:
        return

    history = load_history()

    print("\nConnected to Unix Server. Use shortcuts for quick execution.")
    print("Available commands:", ", ".join(COMMANDS.keys()))
    
    while True:
        # Show top 3 frequently used commands
        if history:
            print("\nMost used commands:", ", ".join([cmd for cmd, _ in history.most_common(3)]))

        cmd = input("\nEnter command (or 'exit' to quit): ").strip().lower()
        
        if cmd == "exit":
            print("Closing connection...")
            save_history(history)
            client.close()
            break
        
        if cmd in COMMANDS:
            command = COMMANDS[cmd]
        else:
            command = cmd  # Execute custom command if not in shortcuts

        print(f"\nExecuting: {command}\n")
        output = execute_command(client, command)
        print(output)

        # Log the command execution
        logging.info(f"Executed command: {command}")
        
        # Update command history
        history[command] += 1

if __name__ == "__main__":
    main()
