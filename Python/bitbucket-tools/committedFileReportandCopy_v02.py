import subprocess
import sys
import os
import pandas as pd
from datetime import datetime
 
def run_git_command(cmd, repo_path):
    """Runs a Git command and returns the output as a list of lines."""
result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
    return result.stdout.strip().split("\n")
 
def get_commit_details(repo_path, branch_name, start_date, end_date, output_dir):
    try:
        # Switch to the specified branch and pull latest changes
subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True)
subprocess.run(["git", "pull"], cwd=repo_path, check=True)
 
        # Convert dates to required format
        start_date = datetime.strptime(start_date, "%d-%m-%Y").strftime("%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%d-%m-%Y").strftime("%Y-%m-%d")
 
        # Get commit details including author and message
        commit_lines = run_git_command(
            ["git", "log", "--since", start_date, "--until", end_date,
             "--pretty=format:%H%n%ci%n%an%n%s%n%b"],
            repo_path
        )
 
        commit_data = []
        file_data = []
 
        for i in range(0, len(commit_lines), 5):
            commit_id = commit_lines[i]
            date_committed = commit_lines[i + 1]
            author = commit_lines[i + 2]
            commit_message = commit_lines[i + 3]
            commit_body = commit_lines[i + 4] if i + 4 < len(commit_lines) else ""
 
            formatted_date = datetime.strptime(date_committed, "%Y-%m-%d %H:%M:%S %z").strftime("%Y%m%d-%H%M")
            commit_folder = os.path.join(output_dir, f"{formatted_date}_{commit_id[:8]}")
            os.makedirs(commit_folder, exist_ok=True)
 
            # Get files changed with statuses
            files_changed_lines = run_git_command(
                ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit_id],
                repo_path
            )
 
            files_details = []
            extracted_files = []
            diff_files = []
 
            for file_line in files_changed_lines:
                if file_line:
                    parts = file_line.split("\t")
                    status, file_path = parts[0], "\t".join(parts[1:])
 
                    file_details = f"{status} - {file_path}"
                    files_details.append(file_details)
 
                    file_entry = {
                        "Commit ID": commit_id,
                        "File Path": file_path,
                        "Change Type": status,
                        "Diff Content": "",
                        "Extracted File Path": "",
                    }
 
                    if status in ["A", "M"]:  # Added or Modified
                        dest_path = os.path.join(commit_folder, os.path.basename(file_path))
 
                        # Extract file content
file_content = subprocess.run(
                            ["git", "show", f"{commit_id}:{file_path}"],
                            cwd=repo_path, capture_output=True, text=True, check=False
                        )
 
                        if file_content.returncode == 0:
                            with open(dest_path, "w", encoding="utf-8") as f:
                                f.write(file_content.stdout)
                            extracted_files.append(dest_path)
                            file_entry["Extracted File Path"] = dest_path
                        else:
                            extracted_files.append("File not found in commit")
 
                    if status == "M":  # Get the diff for modified files
diff_output = subprocess.run(
                            ["git", "diff", f"{commit_id}^!", "--", file_path],
                            cwd=repo_path, capture_output=True, text=True, check=True
                        )
                        diff_file_path = os.path.join(commit_folder, f"{os.path.basename(file_path)}.diff")
 
                        with open(diff_file_path, "w", encoding="utf-8") as diff_file:
                            diff_file.write(diff_output.stdout)
 
                        diff_files.append(diff_file_path)
                        file_entry["Diff Content"] = diff_output.stdout
 
                    file_data.append(file_entry)
 
            commit_data.append([
                commit_id, date_committed, author, commit_message, commit_body,
                ", ".join(files_details), ", ".join(extracted_files), ", ".join(diff_files)
            ])
 
        # Save commit summary to an Excel report
        df_commit_summary = pd.DataFrame(commit_data, columns=[
            "Commit ID", "Date Committed", "Author", "Commit Message", "Commit Body",
            "Files Changed (with Status)", "Extracted Files", "Diff File Paths"
        ])
 
        df_file_changes = pd.DataFrame(file_data)
 
        report_path = os.path.join(output_dir, "commit_report.xlsx")
        with pd.ExcelWriter(report_path) as writer:
            df_commit_summary.to_excel(writer, sheet_name="Commit Summary", index=False)
            df_file_changes.to_excel(writer, sheet_name="File Changes", index=False)
 
        print(f"✅ Commit details saved in {report_path}")
 
    except ValueError:
        print("❌ Error: Invalid date format. Use dd-MM-yyyy.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("❌ Git command error:", e, file=sys.stderr)
 
# Example usage
if __name__ == "__main__":
    repo_path = input("Enter the path to the repository: ").strip()
    branch_name = input("Enter the branch name: ").strip()
    start_date = input("Enter the start date (dd-MM-yyyy): ").strip()
    end_date = input("Enter the end date (dd-MM-yyyy): ").strip()
    output_dir = input("Enter the output directory path: ").strip()
    get_commit_details(repo_path, branch_name, start_date, end_date, output_dir)