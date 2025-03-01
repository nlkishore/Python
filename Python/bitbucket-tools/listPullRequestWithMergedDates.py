import subprocess
import pandas as pd
import sys
from datetime import datetime

# Function to get all merged pull requests
def get_merged_prs():
    try:
        # Get all merged PRs with their commit hashes and dates
        result = subprocess.run(
            ["git", "log", "--merges", "--pretty=format:%H %s %cd", "--date=iso"],
            capture_output=True, text=True, check=True
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
        print("Error fetching merged PRs:", e, file=sys.stderr)
        return []

# Function to get details of a pull request
def get_pr_details(commit_id, merge_date):
    try:
        # Get commit message (to extract source branch)
        commit_message = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_id], 
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Extract source and target branch
        source_branch = None
        target_branch = "main"  # Assuming "main" as the default target

        if "from" in commit_message:
            source_branch = commit_message.split("from ")[1].split(" into")[0].strip()

        # Get changed files in PR
        file_list = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id], 
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")

        # Get first commit in PR (to find requested date)
        first_commit = subprocess.run(
            ["git", "rev-list", "--reverse", commit_id, "--ancestry-path"], 
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")[0]

        first_commit_date = subprocess.run(
            ["git", "show", "-s", "--format=%cd", "--date=iso", first_commit], 
            capture_output=True, text=True, check=True
        ).stdout.strip()

        return commit_id, source_branch, target_branch, first_commit_date, merge_date, ", ".join(file_list)

    except subprocess.CalledProcessError as e:
        print(f"Error fetching details for PR {commit_id}:", e, file=sys.stderr)
        return commit_id, None, None, None, merge_date, ""

# Main execution
if __name__ == "__main__":
    pr_commits = get_merged_prs()
    
    pr_data = []
    for commit, merge_date in pr_commits:
        pr_data.append(get_pr_details(commit, merge_date))

    # Save to Excel
    df = pd.DataFrame(pr_data, columns=["Commit ID", "Source Branch", "Target Branch", "Requested Date", "Merge Completed Date", "Files Changed"])
    df.to_excel("git_pull_requests.xlsx", index=False)

    print("Pull request details saved to git_pull_requests.xlsx")
