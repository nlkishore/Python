import os
import shutil
import subprocess
import time

# Configuration: Update paths as per your setup
BITBUCKET_REPO_URL = "https://your-bitbucket-repo-url.git"
CLONE_DIR = r"C:\your_workspace\project"
ECLIPSE_WORKSPACE_DIR = r"C:\eclipse_workspace"
ECLIPSE_PROJECT_DIR = os.path.join(ECLIPSE_WORKSPACE_DIR, "project")
ECLIPSE_METADATA_DIR = os.path.join(ECLIPSE_WORKSPACE_DIR, ".metadata")
ECLIPSE_SNAP_FILE = os.path.join(ECLIPSE_METADATA_DIR, ".plugins", "org.eclipse.core.resources", ".snap")
ECLIPSE_LOG_FILE = os.path.join(ECLIPSE_METADATA_DIR, ".log")

# Define multiple Tomcat server instances with their CATALINA_BASE values
TOMCAT_SERVERS = {
    "sg-server": {
        "CATALINA_HOME": r"C:\Tomcat9",
        "CATALINA_BASE": r"C:\Tomcat9\sg-server"
    },
    "my-server": {
        "CATALINA_HOME": r"C:\Tomcat10",
        "CATALINA_BASE": r"C:\Tomcat10\my-server"
    }
}

def stop_existing_tomcats():
    """Stops all running Tomcat instances."""
    print("Stopping any running Tomcat instances...")
    if os.name == 'nt':  # Windows
        subprocess.run(["taskkill", "/F", "/IM", "java.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:  # Linux/Mac
        subprocess.run(["pkill", "-f", "java"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Allow processes to stop

def clone_project():
    """Clones or updates the project from BitBucket."""
    if os.path.exists(CLONE_DIR):
        print(f"Updating existing repository: {CLONE_DIR}")
        subprocess.run(["git", "-C", CLONE_DIR, "pull"])
    else:
        print(f"Cloning repository: {BITBUCKET_REPO_URL}")
        subprocess.run(["git", "clone", BITBUCKET_REPO_URL, CLONE_DIR])

def copy_project():
    """Copies the cloned project to Eclipse workspace."""
    if os.path.exists(ECLIPSE_PROJECT_DIR):
        print(f"Deleting existing project at {ECLIPSE_PROJECT_DIR}")
        shutil.rmtree(ECLIPSE_PROJECT_DIR)
    print(f"Copying project to Eclipse workspace: {ECLIPSE_PROJECT_DIR}")
    shutil.copytree(CLONE_DIR, ECLIPSE_PROJECT_DIR)

def refresh_eclipse_workspace():
    """Forces Eclipse to refresh workspace by modifying/deleting key files."""
    if not os.path.exists(ECLIPSE_METADATA_DIR):
        print("Warning: Eclipse workspace metadata folder not found!")
        return

    print("Refreshing Eclipse workspace...")

    # Delete the .snap file to force Eclipse to rescan workspace
    if os.path.exists(ECLIPSE_SNAP_FILE):
        os.remove(ECLIPSE_SNAP_FILE)
        print(f"Deleted {ECLIPSE_SNAP_FILE} to force refresh.")

    # Modify the .log file to trigger detection of change
    with open(ECLIPSE_LOG_FILE, "a") as log_file:
        log_file.write("\n[Eclipse Refresh Triggered]\n")

def start_tomcat(server_name):
    """Starts the selected Tomcat server using catalina.bat start or catalina.sh start."""
    if server_name not in TOMCAT_SERVERS:
        print(f"Error: Invalid server name '{server_name}'. Choose from {list(TOMCAT_SERVERS.keys())}")
        return

    stop_existing_tomcats()  # Stop all running servers before starting

    tomcat_home = TOMCAT_SERVERS[server_name]["CATALINA_HOME"]
    catalina_base = TOMCAT_SERVERS[server_name]["CATALINA_BASE"]
    tomcat_bin = os.path.join(tomcat_home, "bin")
    
    # Set the environment variables dynamically
    os.environ["CATALINA_HOME"] = tomcat_home
    os.environ["CATALINA_BASE"] = catalina_base

    print(f"\nStarting {server_name} with CATALINA_BASE={catalina_base}...\n")

    if os.name == 'nt':  # Windows
        tomcat_cmd = os.path.join(tomcat_bin, "catalina.bat")
        subprocess.Popen([tomcat_cmd, "start"], shell=True, env=os.environ)
    else:  # Linux/Mac
        tomcat_cmd = os.path.join(tomcat_bin, "catalina.sh")
        subprocess.Popen(["sh", tomcat_cmd, "start"], shell=True, env=os.environ)

    time.sleep(5)  # Allow Tomcat to start

def main():
    """Runs the full automation process."""
    clone_project()
    copy_project()
    refresh_eclipse_workspace()

    # Ask user which Tomcat server to start
    print("\nAvailable Tomcat Servers:")
    for server in TOMCAT_SERVERS:
        print(f"- {server}")

    selected_server = input("Enter the Tomcat server to start (sg-server/my-server): ").strip()

    start_tomcat(selected_server)
    print("\n✅ Automation completed successfully!")

if __name__ == "__main__":
    main()
