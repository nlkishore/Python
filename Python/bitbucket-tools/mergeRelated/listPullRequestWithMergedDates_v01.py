import subprocess
import pandas as pd
import os
import sys
import configparser

# Function to read repositories from a properties file
def read_repositories_from_properties(file_path="repositories.properties"):
    config = configparser.ConfigParser()
    config.read(file_path, encoding="utf-8")

    try:
        repo_base_path = config.get("DEFAULT", "repo_base_path").strip()
        repositories = config.get("DEFAULT", "repositories").strip().split(",")
        repositories = [repo.strip() for repo in repositories]
        return repo_base_path, repositories
    except (configparser.NoOptionError, configparser.NoSectionError, FileNotFoundError) as e:
        print(f"Error reading properties file: {e}", file=sys.stderr)
        return None, []

# Function to get all merged pull requests from a repository
def get_merged_prs(repo_path):
    try:
        result = subprocess.run(
            ["git", "log", "--merges", "--pretty=format:%H %s %cd", "--date=iso"],
            capture_output=True, text=True, check=True, encoding="utf-8", cwd=repo_path
        )
        commits = result.stdout.split("\n")

        pr_list = []
        for commit in commits:
            parts = commit.split(" ", 2)
            if len(parts) >= 3 and "Merge pull request" in parts[1]:
                commit_id = parts[0]
                merge_date = " ".join(parts[2:])  # Extract merge date
                pr_list.append((commit_id, merge_date))

        return pr_list
    except subprocess.CalledProcessError as e:
        print(f"Error fetching merged PRs for {repo_path}: {e}", file=sys.stderr)
        return []

# Function to get details of a pull request
def get_pr_details(repo_path, commit_id, merge_date):
    try:
        # Get commit message (to extract source branch)
        commit_message = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_id],
            capture_output=True, text=True, check=True, encoding="utf-8", cwd=repo_path
        ).stdout.strip()

        # Extract source and target branch
        source_branch = None
        target_branch = "main"  # Assuming "main" as the default target

        if "from" in commit_message:
            source_branch = commit_message.split("from ")[1].split(" into")[0].strip()

        # Get changed files in PR
        file_list = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
            capture_output=True, text=True, check=True, encoding="utf-8", cwd=repo_path
        ).stdout.strip().split("\n")

        # Get first commit in PR (to find requested date)
        first_commit = subprocess.run(
            ["git", "rev-list", "--reverse", commit_id, "--ancestry-path"],
            capture_output=True, text=True, check=True, encoding="utf-8", cwd=repo_path
        ).stdout.strip().split("\n")[0]

        first_commit_date = subprocess.run(
            ["git", "show", "-s", "--format=%cd", "--date=iso", first_commit],
            capture_output=True, text=True, check=True, encoding="utf-8", cwd=repo_path
        ).stdout.strip()

        return commit_id, source_branch, target_branch, first_commit_date, merge_date, ", ".join(file_list)

    except subprocess.CalledProcessError as e:
        print(f"Error fetching details for PR {commit_id} in {repo_path}: {e}", file=sys.stderr)
        return commit_id, None, None, None, merge_date, ""

# Main execution
if __name__ == "__main__":
    properties_file = "repositories.properties"
    repo_base_path, repo_names = read_repositories_from_properties(properties_file)

    if not repo_base_path or not repo_names:
        print("No valid repository configuration found. Exiting.", file=sys.stderr)
        sys.exit(1)

    pr_data = []
    
    for repo in repo_names:
        repo_path = os.path.join(repo_base_path, repo)
        
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            print(f"Skipping {repo}: Repository not found at {repo_path}")
            continue

        print(f"Processing repository: {repo}")

        pr_commits = get_merged_prs(repo_path)
        for commit, merge_date in pr_commits:
            pr_data.append([repo] + list(get_pr_details(repo_path, commit, merge_date)))

    # Save to Excel
    df = pd.DataFrame(pr_data, columns=["Repository", "Commit ID", "Source Branch", "Target Branch", "Requested Date", "Merge Completed Date", "Files Changed"])
    df.to_excel("git_pull_requests.xlsx", index=False)

    print("Pull request details saved to git_pull_requests.xlsx")
