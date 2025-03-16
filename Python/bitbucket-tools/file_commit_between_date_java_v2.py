import os
import subprocess
from datetime import datetime

# Repository details
repo_path = "path_to_local_repo"
common_location = "path_to_common_location"
branch_name = "branch_name"

# Date range for commits
start_date = "2025-03-01"
end_date = "2025-03-15"

def switch_branch_and_pull(branch):
    subprocess.run(["git", "checkout", branch], cwd=repo_path)
    subprocess.run(["git", "pull"], cwd=repo_path)

def get_commits_between_dates():
    log_format = "--pretty=format:%H"
    date_range = f"--since={start_date} --until={end_date}"
    commits = subprocess.check_output(["git", "log", date_range, log_format], cwd=repo_path).decode().splitlines()
    return commits

def copy_java_files(commit):
    subprocess.run(["git", "checkout", commit], cwd=repo_path)
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                dest_path = os.path.join(common_location, os.path.relpath(file_path, repo_path))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                subprocess.run(["cp", file_path, dest_path])

def main():
    switch_branch_and_pull(branch_name)
    commits = get_commits_between_dates()
    for commit in commits:
        copy_java_files(commit)

    # Overwrite the latest committed file
    latest_commit = subprocess.check_output(["git", "log", "-1", "--pretty=format:%H"], cwd=repo_path).decode().strip()
    copy_java_files(latest_commit)

if __name__ == "__main__":
    main()