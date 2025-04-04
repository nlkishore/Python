import subprocess
import sys
import os
import logging
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        filename="git_merge.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def run_git_command(command, repo_path):
    try:
        result = subprocess.run(command, cwd=repo_path, capture_output=True, text=True, check=True)
        logging.info(f"Command {' '.join(command)} executed successfully.")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {' '.join(command)}: {e.stderr}")
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def merge_all_commits(repo_path, source_branch, target_branch):
    logging.info(f"Merging all commits from {source_branch} to {target_branch}")
    run_git_command(["git", "checkout", target_branch], repo_path)
    run_git_command(["git", "pull"], repo_path)
    run_git_command(["git", "merge", "--no-ff", source_branch], repo_path)
    run_git_command(["git", "push", "origin", target_branch], repo_path)
    print(f"Successfully merged all commits from {source_branch} to {target_branch}")

def merge_specific_commits(repo_path, source_branch, target_branch, specific_commits):
    logging.info(f"Merging specific commits from {source_branch} to {target_branch}")
    run_git_command(["git", "checkout", target_branch], repo_path)
    run_git_command(["git", "pull"], repo_path)
    for commit in specific_commits:
        run_git_command(["git", "cherry-pick", commit], repo_path)
    run_git_command(["git", "push", "origin", target_branch], repo_path)
    print(f"Successfully merged specific commits from {source_branch} to {target_branch}")

def merge_release_to_release(repo_path, source_branch, target_branch):
    logging.info(f"Merging {source_branch} into {target_branch}")
    run_git_command(["git", "checkout", target_branch], repo_path)
    run_git_command(["git", "pull"], repo_path)
    run_git_command(["git", "merge", "--no-ff", source_branch], repo_path)
    run_git_command(["git", "push", "origin", target_branch], repo_path)
    print(f"Successfully merged {source_branch} into {target_branch}")

if __name__ == "__main__":
    setup_logging()
    repo_path = input("Enter the path to the repository: ").strip()
    source_branch = input("Enter the source branch name: ").strip()
    target_branch = input("Enter the target branch name: ").strip()
    merge_type = input("Select merge type: 1 - All commits, 2 - Specific commits, 3 - Release to Release: ").strip()
    
    if merge_type == "1":
        merge_all_commits(repo_path, source_branch, target_branch)
    elif merge_type == "2":
        specific_commits = input("Enter specific commit IDs (comma-separated): ").strip().split(",")
        merge_specific_commits(repo_path, source_branch, target_branch, specific_commits)
    elif merge_type == "3":
        merge_release_to_release(repo_path, source_branch, target_branch)
    else:
        print("Invalid selection.")
        sys.exit(1)
