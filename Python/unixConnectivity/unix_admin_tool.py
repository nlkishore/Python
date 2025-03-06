import os
import subprocess
import logging
import configparser
import datetime
import json
from collections import Counter

# Configure logging
LOG_FILE = "/var/log/unix_admin_tool.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Files for storing history and commands
HISTORY_FILE = "/var/tmp/command_history.json"
COMMANDS_FILE = "/var/tmp/commands.ini"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

def check_and_generate_ssh_keys():
    """Check if SSH keys exist, generate if not."""
    if not os.path.exists(SSH_KEY_PATH):
        print("SSH key not found. Generating one...")
        subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", os.path.expanduser("~/.ssh/id_rsa"), "-N", ""])
        print("SSH key generated at ~/.ssh/id_rsa.pub")
    else:
        print("SSH key already exists.")

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

def execute_command(command):
    """Execute a shell command and return the output."""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.output}"

def find_string_occurrences(log_file, search_string):
    """Find the first and last occurrence of a search string in a log file and retrieve lines between them."""
    
    # Get line numbers of occurrences
    grep_command = f"grep -n '{search_string}' {log_file}"
    grep_output = execute_command(grep_command)

    if "Error" in grep_output or not grep_output.strip():
        print(f"\nNo occurrences of '{search_string}' found in {log_file}.")
        return

    # Extract line numbers
    lines = grep_output.strip().split("\n")
    line_numbers = [int(line.split(":")[0]) for line in lines]

    if not line_numbers:
        print(f"\nNo valid occurrences found for '{search_string}' in {log_file}.")
        return

    first_line = min(line_numbers)
    last_line = max(line_numbers)

    print(f"\nFirst occurrence of '{search_string}' at line: {first_line}")
    print(f"Last occurrence of '{search_string}' at line: {last_line}")

    # Fetch lines between first and last occurrence
    sed_command = f"sed -n '{first_line},{last_line}p' {log_file}"
    log_data = execute_command(sed_command)

    print("\nExtracted Log Data:\n" + log_data)

def fetch_logs_between_times(log_file, start_time, end_time):
    """Retrieve log entries between a start and end time."""
    awk_command = f"awk '$0 >= \"{start_time}\" && $0 <= \"{end_time}\"' {log_file}"
    logs = execute_command(awk_command)
    print("\nLogs between given time range:\n" + logs)

def main():
    """Main function to handle user input and execute commands."""
    check_and_generate_ssh_keys()
    
    commands = load_commands()
    history = load_history()

    print("\nRunning on Unix Machine. Use shortcuts for quick execution.")
    print("Available shortcuts:", ", ".join(commands.keys()))
    
    while True:
        # Show top 3 frequently used commands
        if history:
            print("\nMost used commands:", ", ".join([cmd for cmd, _ in history.most_common(3)]))

        cmd = input("\nEnter shortcut or command (or 'findstring' to search logs, 'fetchlogs' for time-based logs, 'exit' to quit): ").strip().lower()
        
        if cmd == "exit":
            print("Exiting...")
            save_history(history)
            break
        
        elif cmd == "findstring":
            log_file = input("Enter log file path (e.g., /var/log/syslog): ").strip()
            search_string = input("Enter search string: ").strip()

            find_string_occurrences(log_file, search_string)
            continue
        
        elif cmd == "fetchlogs":
            log_file = input("Enter log file path (e.g., /var/log/syslog): ").strip()
            start_time = input("Enter start time (YYYY-MM-DD HH:MM:SS): ").strip()
            end_time = input("Enter end time (YYYY-MM-DD HH:MM:SS): ").strip()

            fetch_logs_between_times(log_file, start_time, end_time)
            continue

        command = commands.get(cmd, cmd)  # Use shortcut or raw command

        print(f"\nExecuting: {command}\n")
        output = execute_command(command)
        print(output)

        # Log the command execution
        logging.info(f"Executed command: {command}")
        
        # Update command history
        history[command] += 1

if __name__ == "__main__":
    main()
