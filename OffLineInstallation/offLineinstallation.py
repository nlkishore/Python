import os
import subprocess
import shutil

# === CONFIGURATION ===
REQUIREMENTS = [
    "langgraph-cli==0.0.25",
    "langchain==0.1.20",
    "langchain-openai==0.1.3",
    "python-dotenv==1.0.1"
]
PACKAGE_DIR = "offline_packages"
REQUIREMENTS_FILE = "requirements.txt"
ARCHIVE_NAME = "offline_bundle.zip"

# === STEP 1: Create requirements.txt ===
def write_requirements():
    with open(REQUIREMENTS_FILE, "w") as f:
        f.write("\n".join(REQUIREMENTS))
    print(f"[✓] Created {REQUIREMENTS_FILE}")

# === STEP 2: Download packages ===
def download_packages():
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    subprocess.run([
        "pip", "download", "-r", REQUIREMENTS_FILE, "-d", PACKAGE_DIR
    ], check=True)
    print(f"[✓] Packages downloaded to {PACKAGE_DIR}")

# === STEP 3: Archive for transfer ===
def archive_bundle():
    shutil.make_archive("offline_bundle", "zip", PACKAGE_DIR)
    print(f"[✓] Created archive: {ARCHIVE_NAME}")

# === STEP 4: Generate install script for offline machine ===
def generate_offline_script():
    with open("install_offline.sh", "w") as f:
        f.write(f"""#!/bin/bash
python -m venv langgraph_env
source langgraph_env/bin/activate
pip install --no-index --find-links={PACKAGE_DIR} -r {REQUIREMENTS_FILE}
""")
    print("[✓] Generated install_offline.sh")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    write_requirements()
    download_packages()
    archive_bundle()
    generate_offline_script()
    print("\n🎉 Offline installer bundle is ready for transfer!")