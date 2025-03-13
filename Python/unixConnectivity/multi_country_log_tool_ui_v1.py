import paramiko
import configparser
import logging
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

# Configure Logging
LOG_FILE = "unix_tool.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR=Path(__file__).resolve().parent
# Load configurations
server_config = configparser.ConfigParser()
server_config.read(BASE_DIR/ "servers_v1.ini")

commands_config = configparser.ConfigParser()
commands_config.read(BASE_DIR/ "commands_v1.ini")

def connect_and_execute():
    market = market_var.get()
    command_key = command_var.get()
    custom_command = custom_command_var.get().strip()

    if not market:
        messagebox.showerror("Error", "Please select a market.")
        return

    if market not in server_config:
        messagebox.showerror("Error", f"Market '{market}' not found in configuration.")
        return

    host = server_config[market]["host"]
    user = server_config[market]["user"]
    password = server_config[market].get("password", None)
    key_file = server_config[market].get("key_file", None)

    # Use either a shortcut command or a custom command
    if command_key and market in commands_config and command_key in commands_config[market]:
        command = commands_config[market][command_key]
    elif custom_command:
        command = custom_command
    else:
        messagebox.showerror("Error", "Please select a shortcut or enter a custom command.")
        return

    try:
        log_message = f"Connecting to {host} as {user}..."
        logging.info(log_message)
        update_output(log_message)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if password:
            ssh.connect(hostname=host, username=user, password=password)
        else:
            ssh.connect(hostname=host, username=user, key_filename=key_file)

        log_message = f"Executing: {command}"
        logging.info(log_message)
        update_output(log_message)

        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error_output = stderr.read().decode()

        if output:
            logging.info(f"Command Output:\n{output}")
            update_output(output)

        if error_output:
            logging.error(f"Command Error:\n{error_output}")
            update_output(error_output)

        ssh.close()
    except Exception as e:
        error_msg = f"Connection Error: {str(e)}"
        logging.error(error_msg)
        messagebox.showerror("Connection Error", error_msg)

def update_commands(*args):
    """Update the available command list when a market is selected."""
    command_listbox.delete(0, tk.END)
    selected_market = market_var.get()
    if selected_market in commands_config:
        for cmd in commands_config[selected_market]:
            command_listbox.insert(tk.END, cmd)

def select_command(event):
    """Update the selected command variable when an item is clicked."""
    selected_index = command_listbox.curselection()
    if selected_index:
        command_var.set(command_listbox.get(selected_index))

def update_output(message):
    """Update the output box with log messages."""
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, message + "\n")
    output_text.config(state=tk.DISABLED)
    output_text.yview(tk.END)  # Auto-scroll to the latest message

# GUI Setup
root = tk.Tk()
root.title("Unix Server Command Executor")
root.geometry("500x450")

# Market Selection
ttk.Label(root, text="Select Market:").pack()
market_var = tk.StringVar()
market_dropdown = ttk.Combobox(root, textvariable=market_var, values=list(server_config.sections()), state="readonly")
market_dropdown.pack()
market_dropdown.bind("<<ComboboxSelected>>", update_commands)

# Command Selection (Shortcut)
ttk.Label(root, text="Select Command Shortcut:").pack()
command_var = tk.StringVar()
command_listbox = tk.Listbox(root, height=6)
command_listbox.pack()
command_listbox.bind("<<ListboxSelect>>", select_command)

# Custom Command Input
ttk.Label(root, text="Or Enter Custom Command:").pack()
custom_command_var = tk.StringVar()
custom_command_entry = ttk.Entry(root, textvariable=custom_command_var, width=50)
custom_command_entry.pack()

# Execute Button
execute_button = ttk.Button(root, text="Execute", command=connect_and_execute)
execute_button.pack(pady=10)

# Output Area
ttk.Label(root, text="Output:").pack()
output_text = scrolledtext.ScrolledText(root, height=10, state=tk.DISABLED)
output_text.pack()

# Run the GUI
root.mainloop()
