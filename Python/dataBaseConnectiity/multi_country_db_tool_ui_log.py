import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import cx_Oracle
import configparser
import pandas as pd
from tabulate import tabulate
from pathlib import Path
import logging

# Configure logging
LOG_FILE = "app.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load configurations
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "databases.ini"
COMMANDS_FILE = BASE_DIR / "commands.ini"

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
db_configs = {section: dict(config[section]) for section in config.sections() if section.startswith("database_")}

commands_config = configparser.ConfigParser()
commands_config.read(COMMANDS_FILE)
commands_dict = {section: dict(commands_config[section]) for section in commands_config.sections()}

# Function to update commands dropdown based on selected country
def update_commands(*args):
    selected_country = country_var.get()
    command_dropdown["values"] = list(commands_dict.get(selected_country, {}).keys())
    command_var.set("")

# Function to execute Unix command
def execute_command():
    selected_country = country_var.get()
    selected_command = command_var.get()
    
    if not selected_command:
        output_text.insert(tk.END, "\n❌ Please select a command!\n")
        return
    
    cmd = commands_dict[selected_country][selected_command]
    logging.info(f"Executing command for {selected_country}: {cmd}")
    
    try:
        output = subprocess.check_output(cmd, shell=True, text=True)
        output_text.insert(tk.END, f"\n$ {cmd}\n{output}\n")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e.output}")
        output_text.insert(tk.END, f"\n❌ Error executing command:\n{e.output}\n")

# Function to execute DB query
def execute_db_query():
    selected_country = country_var.get()
    query = query_text.get("1.0", tk.END).strip()
    
    if not query:
        output_text.insert(tk.END, "\n❌ Please enter a SQL query!\n")
        return
    
    db_config = db_configs.get(f"database_{selected_country}")
    if not db_config:
        output_text.insert(tk.END, f"\n❌ No database config found for {selected_country}\n")
        return
    
    try:
        logging.info(f"Executing SQL Query for {selected_country}: {query}")
        dsn = cx_Oracle.makedsn(db_config["host"], db_config["port"], service_name=db_config["service_name"])
        connection = cx_Oracle.connect(user=db_config["username"], password=db_config["password"], dsn=dsn)
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # Convert BLOB and CLOB to readable format
        formatted_rows = []
        for row in rows:
            formatted_row = []
            for col, value in zip(columns, row):
                if isinstance(value, cx_Oracle.LOB):
                    formatted_row.append(value.read()[:500])  # Read first 500 chars for display
                else:
                    formatted_row.append(value)
            formatted_rows.append(formatted_row)
        
        # Format output in table
        table_output = tabulate(formatted_rows, headers=columns, tablefmt="grid")
        output_text.insert(tk.END, f"\nSQL Query: {query}\n")
        output_text.insert(tk.END, f"\n{table_output}\n")
        
    except Exception as e:
        logging.error(f"Database error for {selected_country}: {e}")
        output_text.insert(tk.END, f"\n❌ Database Error: {e}\n")
    
    finally:
        cursor.close()
        connection.close()

# UI Setup
root = tk.Tk()
root.title("Multi-Country Database & Command Tool")
root.geometry("600x500")

# Country Selection
tk.Label(root, text="Select Country:").pack()
country_var = tk.StringVar()
country_dropdown = ttk.Combobox(root, textvariable=country_var, values=list(commands_dict.keys()))
country_dropdown.pack()
country_var.trace("w", update_commands)

# Command Selection
tk.Label(root, text="Select Command:").pack()
command_var = tk.StringVar()
command_dropdown = ttk.Combobox(root, textvariable=command_var)
command_dropdown.pack()

# Execute Command Button
tk.Button(root, text="Run Command", command=execute_command).pack()

# Query Input
tk.Label(root, text="Enter SQL Query:").pack()
query_text = scrolledtext.ScrolledText(root, height=5, width=50)
query_text.pack()

# Execute Query Button
tk.Button(root, text="Run Query", command=execute_db_query).pack()

# Output Box
tk.Label(root, text="Output:").pack()
output_text = scrolledtext.ScrolledText(root, height=10, width=70)
output_text.pack()

# Run UI
root.mainloop()
