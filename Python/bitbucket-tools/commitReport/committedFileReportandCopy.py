import subprocess
import sys
import os
import shutil
import pandas as pd
from datetime import datetime

def get_commit_details(repo_path, start_date, end_date, output_dir):
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
        
        commit_data = []
        for i in range(0, len(commit_lines), 3):
            commit_id = commit_lines[i]
            date_committed = commit_lines[i + 1]
            head_refs = commit_lines[i + 2] if len(commit_lines) > i + 2 else ""
            
            # Format date for folder name
            formatted_date = datetime.strptime(date_committed, "%Y-%m-%d %H:%M:%S %z").strftime("%Y%m%d-%H%M%S")
            commit_folder_name = f"{formatted_date}_{commit_id}"
            commit_folder = os.path.join(output_dir, commit_folder_name)
            os.makedirs(commit_folder, exist_ok=True)
            
            # Get files changed in the commit
            cmd_files_changed = ["git", "show", "--pretty=format:", "--name-only", commit_id]
            files_changed_info = subprocess.run(cmd_files_changed, cwd=repo_path, capture_output=True, text=True, check=True)
            files_changed = files_changed_info.stdout.strip().split("\n")
            
            file_paths = []
            for file in files_changed:
                file_path = os.path.join(repo_path, file)
                if file:
                    # Extract file content from the specific commit
                    cmd_checkout = ["git", "show", f"{commit_id}:{file}"]
                    file_content = subprocess.run(cmd_checkout, cwd=repo_path, capture_output=True, text=True, check=False)
                    
                    if file_content.returncode == 0:
                        dest_path = os.path.join(commit_folder, os.path.basename(file))
                        with open(dest_path, "w", encoding="utf-8") as f:
                            f.write(file_content.stdout)
                        file_paths.append(dest_path)
                    else:
                        file_paths.append("File not found in commit")
            
            commit_data.append([commit_id, date_committed, ", ".join(files_changed), ", ".join(file_paths)])
        
        # Save details to an Excel report
        df = pd.DataFrame(commit_data, columns=["Commit ID", "Date Committed", "Files Changed", "Copied File Paths"])
        report_path = os.path.join(output_dir, "commit_report.xlsx")
        df.to_excel(report_path, index=False)
        
        print(f"Commit details saved in {report_path}")
    except ValueError:
        print("Error in date format. Please use dd-MM-yyyy.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("Error executing Git command:", e, file=sys.stderr)

# Example usage
if __name__ == "__main__":
    repo_path = input("Enter the path to the repository: ").strip()
    start_date = input("Enter the start date (dd-MM-yyyy): ").strip()
    end_date = input("Enter the end date (dd-MM-yyyy): ").strip()
    output_dir = input("Enter the output directory path: ").strip()
    get_commit_details(repo_path, start_date, end_date, output_dir)
