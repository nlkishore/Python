import subprocess
import os
import sys
import shutil
import configparser
import urllib.parse

def encode_credentials(username, password):
    """Encodes credentials to safely use them in a Git URL."""
    encoded_password = urllib.parse.quote(password, safe="")
    return f"{username}:{encoded_password}"

def read_repo_config(file_path):
    """Reads repository configuration from a properties file."""
    config = configparser.ConfigParser()
    config.read(file_path, encoding="utf-8")

    try:
        git_base_url = config.get("DEFAULT", "git_base_url").strip()
        repo_base_path = config.get("DEFAULT", "repo_base_path").strip()
        repo_list = config.get("DEFAULT", "repositories").strip().split(",")
        branch_list = config.get("DEFAULT", "branches", fallback="master").strip().split(",")

        repositories = {repo.strip(): branch_list[i].strip() if i < len(branch_list) else "master"
                        for i, repo in enumerate(repo_list)}

        username = config.get("DEFAULT", "username", fallback=None)
        password = config.get("DEFAULT", "password", fallback=None)

        return git_base_url, repo_base_path, repositories, username, password
    except (configparser.NoOptionError, configparser.NoSectionError, FileNotFoundError) as e:
        print(f"Error reading properties file: {e}", file=sys.stderr)
        return None, None, {}, None, None

def cleanup_local_repos(repo_base_path, repositories):
    """Deletes local repositories if they already exist."""
    for repo in repositories.keys():
        repo_path = os.path.join(repo_base_path, repo)
        if os.path.exists(repo_path):
            print(f"Deleting existing repository: {repo_path}")
            try:
                shutil.rmtree(repo_path)  
            except Exception as e:
                print(f"Failed to delete {repo_path}: {e}", file=sys.stderr)

def clone_repos(git_base_url, repo_base_path, repositories, username=None, password=None):
    """Clones all remote repositories and checks out the correct branches."""
    if not os.path.exists(repo_base_path):
        os.makedirs(repo_base_path)  

    for repo, branch in repositories.items():
        if username and password:
            encoded_credentials = encode_credentials(username, password)
            auth_url = git_base_url.replace("https://", f"https://{encoded_credentials}@")
        else:
            auth_url = git_base_url

        repo_url = f"{auth_url}{repo}.git"
        repo_path = os.path.join(repo_base_path, repo)

        print(f"Cloning repository: {repo_url} into {repo_path}")
        try:
            subprocess.run(["git", "clone", repo_url, repo_path], check=True, text=True)
            print(f"Successfully cloned {repo}")

            if branch:
                print(f"Checking out branch: {branch} in {repo}")
                subprocess.run(["git", "-C", repo_path, "checkout", branch], check=True, text=True)

        except subprocess.CalledProcessError as e:
            print(f"Failed to clone {repo_url}: {e}", file=sys.stderr)

if __name__ == "__main__":
    properties_file = "/Users/yaswitha/k8s/python/Python/Python/bitbucket-tools/repositories.properties"
    git_base_url, repo_base_path, repo_names, username, password = read_repo_config(properties_file)

    if not git_base_url or not repo_base_path or not repo_names:
        print("Invalid configuration. Exiting.", file=sys.stderr)
        sys.exit(1)

    cleanup_local_repos(repo_base_path, repo_names)
    clone_repos(git_base_url, repo_base_path, repo_names, username, password)

    print("All repositories are cleaned up and cloned successfully!")
