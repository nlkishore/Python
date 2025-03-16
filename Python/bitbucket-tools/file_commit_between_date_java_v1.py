import os
import subprocess

# Repository details
repo_url = "https://bitbucket.org/repo_owner/repo_slug.git"
common_location = "path_to_common_location"

# Clone the repository
subprocess.run(["git", "clone", repo_url])
os.chdir("repo_slug")

# Get the list of commits between the specified dates
commits = subprocess.check_output(["git", "log", "--since=2025-03-01", "--until=2025-03-15", "--pretty=format:%H"]).decode().splitlines()

# Iterate through the commits and copy Java files to the common location
for commit in commits:
    subprocess.run(["git", "checkout", commit])
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                dest_path = os.path.join(common_location, os.path.basename(file_path))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                subprocess.run(["cp", file_path, dest_path])

# Overwrite the latest committed file
latest_commit = subprocess.check_output(["git", "log", "-1", "--pretty=format:%H"]).decode().strip()
subprocess.run(["git", "checkout", latest_commit])
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".java"):
            file_path = os.path.join(root, file)
            dest_path = os.path.join(common_location, os.path.basename(file_path))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            subprocess.run(["cp", file_path, dest_path])

print(f"Java files copied to {common_location} and latest committed file overwritten.")

 