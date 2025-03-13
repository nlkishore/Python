import os
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import logging

# Configure logging
logging.basicConfig(filename="folder_copy.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def select_source():
    source_path.set(filedialog.askdirectory())

def select_destination():
    destination_path.set(filedialog.askdirectory())

def perform_copy():
    source = source_path.get()
    destination = destination_path.get()
    method = method_var.get()

    if not source or not destination:
        messagebox.showerror("Error", "Source and destination folders must be selected.")
        logging.error("Source or destination folder not selected.")
        return

    try:
        logging.info(f"Starting folder copy: Source={source}, Destination={destination}, Method={method}")
        if method == "Robocopy (Windows)":
            if os.name == 'nt':  # Ensure Windows system
                subprocess.run(["robocopy", source, destination, "/E"], check=True)
            else:
                raise EnvironmentError("Robocopy is not available on this system.")
        elif method == "Tar (Unix/Linux)":
            subprocess.run(["tar", "-cf", f"{destination}/archive.tar", "-C", source, "."], check=True)
        elif method == "Zip & Unzip":
            zip_file = f"{destination}/archive.zip"
            shutil.make_archive(zip_file.replace(".zip", ""), 'zip', source)
            shutil.unpack_archive(zip_file, destination)
        elif method == "Basic Copy":
            shutil.copytree(source, destination, dirs_exist_ok=True)
        elif method == "Compact & Compress":
            shutil.make_archive(f"{destination}/compressed", 'gztar', source)
        else:
            raise ValueError("Invalid copy method selected.")
        
        messagebox.showinfo("Success", f"Folder copied successfully using {method}.")
        logging.info(f"Successfully copied folder using {method}.")
    except Exception as e:
        error_message = f"Failed to copy folder: {e}"
        messagebox.showerror("Error", error_message)
        logging.error(error_message)

# Create the GUI window
window = tk.Tk()
window.title("Folder Copy Utility with Logging")
window.geometry("500x400")

# Variables
source_path = tk.StringVar()
destination_path = tk.StringVar()
method_var = tk.StringVar()

# UI Elements
tk.Label(window, text="Source Folder:").pack(pady=5)
tk.Entry(window, textvariable=source_path, width=50).pack()
tk.Button(window, text="Browse", command=select_source).pack(pady=5)

tk.Label(window, text="Destination Folder:").pack(pady=5)
tk.Entry(window, textvariable=destination_path, width=50).pack()
tk.Button(window, text="Browse", command=select_destination).pack(pady=5)

tk.Label(window, text="Copy Method:").pack(pady=5)
methods = ["Robocopy (Windows)", "Tar (Unix/Linux)", "Zip & Unzip", "Basic Copy", "Compact & Compress"]
for method in methods:
    tk.Radiobutton(window, text=method, variable=method_var, value=method).pack(anchor="w")

tk.Button(window, text="Copy Folder", command=perform_copy).pack(pady=10)

# Start the GUI event loop
window.mainloop()
