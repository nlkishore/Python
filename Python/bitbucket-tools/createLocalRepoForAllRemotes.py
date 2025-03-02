import subprocess
import os
import sys
import shutil
import configparser

def read_repo_config(file_path="repositories.properties"):
    """Reads repository configuration from a properties file."""
    config = configparser.ConfigParser()
    config.read(file_path, encoding="utf-8")

    try:
        git_base_url = config.get("DEFAULT", "git_base_url").strip()
        repo_base_path = config.get("DEFAULT", "repo_base_path").strip()
        repositories = config.get("DEFAULT", "repositories").strip().split(",")
        repositories = [repo.strip() for repo in repositories]

        # Read username and password/token if available
        username = config.get("DEFAULT", "username", fallback=None)
        password = config.get("DEFAULT", "password", fallback=None)

        return git_base_url, repo_base_path, repositories, username, password
    except (configparser.NoOptionError, configparser.NoSectionError, FileNotFoundError) as e:
        print(f"Error reading properties file: {e}", file=sys.stderr)
        return None, None, [], None, None

def cleanup_local_repos(repo_base_path, repositories):
    """Deletes local repositories if they already exist."""
    for repo in repositories:
        repo_path = os.path.join(repo_base_path, repo)
        if os.path.exists(repo_path):
            print(f"Deleting existing repository: {repo_path}")
            try:
                shutil.rmtree(repo_path)  # Deletes the folder and its contents
            except Exception as e:
                print(f"Failed to delete {repo_path}: {e}", file=sys.stderr)

def clone_repos(git_base_url, repo_base_path, repositories, username=None, password=None):
    """Clones all remote repositories to the local system with optional authentication."""
    if not os.path.exists(repo_base_path):
        os.makedirs(repo_base_path)  # Create the base directory if it doesn't exist

    for repo in repositories:
        if username and password:
            # Insert credentials into the URL (Basic Authentication)
            auth_url = git_base_url.replace("https://", f"https://{username}:{password}@")
        else:
            auth_url = git_base_url

        repo_url = f"{auth_url}{repo}.git"
        repo_path = os.path.join(repo_base_path, repo)

        print(f"Cloning repository: {repo_url} into {repo_path}")
        try:
            subprocess.run(["git", "clone", repo_url, repo_path], check=True, text=True)
            print(f"Successfully cloned {repo}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone {repo_url}: {e}", file=sys.stderr)

if __name__ == "__main__":
    properties_file = "repositories.properties"
    git_base_url, repo_base_path, repo_names, username, password = read_repo_config(properties_file)

    if not git_base_url or not repo_base_path or not repo_names:
        print("Invalid configuration. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Step 1: Cleanup existing local repositories
    cleanup_local_repos(repo_base_path, repo_names)

    # Step 2: Clone fresh repositories with authentication
    clone_repos(git_base_url, repo_base_path, repo_names, username, password)

    print("All repositories are cleaned up and cloned successfully!")
