import os
import subprocess
import shutil

# Configuration
REPO_URL = "https://github.com/example/repo.git"  # Change this to your repo
BRANCHES = ["feature-branch-1", "feature-branch-2", "feature-branch-3"]
WORKING_DIR = r"C:\Projects\working_dir"
ECLIPSE_WORKSPACE = r"C:\Projects\eclipse\workspace"

# Ensure working directory exists
if not os.path.exists(WORKING_DIR):
    os.makedirs(WORKING_DIR)

for branch in BRANCHES:
    repo_dir = os.path.join(WORKING_DIR, branch)
    
    if os.path.exists(repo_dir):
        print(f"Updating {branch} in {repo_dir}...")
        subprocess.run(["git", "-C", repo_dir, "fetch"], check=True)
        subprocess.run(["git", "-C", repo_dir, "checkout", branch], check=True)
        subprocess.run(["git", "-C", repo_dir, "pull"], check=True)
    else:
        print(f"Cloning {branch} to {repo_dir}...")
        subprocess.run(["git", "clone", "-b", branch, REPO_URL, repo_dir], check=True)

    # Copy the project to Eclipse workspace
    eclipse_project_path = os.path.join(ECLIPSE_WORKSPACE, branch)
    
    if os.path.exists(eclipse_project_path):
        print(f"Removing existing project: {eclipse_project_path}")
        shutil.rmtree(eclipse_project_path)

    print(f"Copying {repo_dir} to Eclipse workspace: {eclipse_project_path}")
    shutil.copytree(repo_dir, eclipse_project_path)

print("All branches synced and associated with Eclipse workspace.")
