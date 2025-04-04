#Git commands to retrieve commit details, including the Commit ID, Date Committed, HEAD branch, and the list of files changed in that commit. The script assumes that you have a local clone of the Bitbucket
import subprocess
import sys
from datetime import datetime

def get_commit_details(repo_path, months):
    try:
        # Get commits from the past few months
        cmd_commit_info = [
            "git", "log", "--since", f"{months}.months", "--pretty=format:%H%n%ci%n%D"
        ]
        commit_info = subprocess.run(cmd_commit_info, cwd=repo_path, capture_output=True, text=True, check=True)
        commit_lines = commit_info.stdout.strip().split("\n")
        
        for i in range(0, len(commit_lines), 3):
            commit_id = commit_lines[i]
            date_committed = commit_lines[i + 1]
            head_refs = commit_lines[i + 2] if len(commit_lines) > i + 2 else ""
            
            print("Commit ID:", commit_id)
            print("Date Committed:", date_committed)
            print("HEAD Reference:", head_refs)
            print("-------------------------")
    except subprocess.CalledProcessError as e:
        print("Error executing Git command:", e, file=sys.stderr)


def get_commit_details(repo_path, start_date, end_date):
    try:
        # Convert dates to the required format
        start_date = datetime.strptime(start_date, "%d-%m-%Y").strftime("%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%d-%m-%Y").strftime("%Y-%m-%d")
        
        # Get commits between the given dates
        cmd_commit_info = [
            "git", "log", "--since", start_date, "--until", end_date, "--pretty=format:%H%n%ci%n%D"
        ]
        commit_info = subprocess.run(cmd_commit_info, cwd=repo_path, capture_output=True, text=True, check=True)
        commit_lines = commit_info.stdout.strip().split("\n")
        
        for i in range(0, len(commit_lines), 3):
            commit_id = commit_lines[i]
            date_committed = commit_lines[i + 1]
            head_refs = commit_lines[i + 2] if len(commit_lines) > i + 2 else ""
            
            print("Commit ID:", commit_id)
            print("Date Committed:", date_committed)
            print("HEAD Reference:", head_refs)
            print("-------------------------")
    except ValueError as ve:
        print("Error in date format. Please use dd-MM-yyyy.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("Error executing Git command:", e, file=sys.stderr)

# Example usage
if __name__ == "__main__":
    repo_path = input("Enter the path to the repository: ").strip()
    months = input("Enter the number of months to look back: ").strip()
    get_commit_details(repo_path, months)

    repo_path = input("Enter the path to the repository: ").strip()
    start_date = input("Enter the start date (dd-MM-yyyy): ").strip()
    end_date = input("Enter the end date (dd-MM-yyyy): ").strip()
    get_commit_details(repo_path, start_date, end_date)
