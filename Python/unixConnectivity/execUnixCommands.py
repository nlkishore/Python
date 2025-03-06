import paramiko
import time

# Define the Unix server details
HOST = "your_unix_server"
PORT = 22
USERNAME = "your_username"
PASSWORD = "your_password"  # Ideally, use key authentication or a secure vault
SUDO_PASSWORD = "your_sudo_password"

# Predefined command shortcuts for quick execution
COMMANDS = {
    "disk": "df -h",
    "mem": "free -m",
    "cpu": "top -bn1 | head -n 10",
    "logs": "sudo tail -f /var/log/syslog",
    "users": "who",
    "uptime": "uptime",
    "processes": "ps aux --sort=-%cpu | head -10",
}

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

    print("\nConnected to Unix Server. Use shortcuts for quick execution.")
    print("Available commands:", ", ".join(COMMANDS.keys()))
    
    while True:
        cmd = input("\nEnter command (or 'exit' to quit): ").strip().lower()
        
        if cmd == "exit":
            print("Closing connection...")
            client.close()
            break
        
        if cmd in COMMANDS:
            command = COMMANDS[cmd]
        else:
            command = cmd  # Execute custom command if not in shortcuts

        print(f"\nExecuting: {command}\n")
        output = execute_command(client, command)
        print(output)

if __name__ == "__main__":
    main()
