import logging
from flask import Flask, render_template, request, jsonify
import git
import os

# Configure logging
logging.basicConfig(filename='bitbucket_ui.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
REPO_URL = "https://github.com/nlkishore/Python.git"  # Update with the actual repo name
LOCAL_REPO_PATH = "./local_repo"

# Clone the repository if it does not exist
if not os.path.exists(LOCAL_REPO_PATH):
    logging.info(f"Cloning repository {REPO_URL}")
    repo = git.Repo.clone_from(REPO_URL, LOCAL_REPO_PATH)
else:
    repo = git.Repo(LOCAL_REPO_PATH)
    repo.remotes.origin.pull()
    logging.info("Pulled latest changes from remote repository")

@app.route('/')
def index():
    branches = [branch.name for branch in repo.remotes.origin.refs]
    logging.info("Loaded branches for UI")
    return render_template('index.html', branches=branches)

@app.route('/switch_branch', methods=['POST'])
def switch_branch():
    data = request.json
    branch_name = data.get('branch')
    try:
        repo.git.checkout(branch_name)
        repo.remotes.origin.pull()
        logging.info(f"Switched to branch {branch_name}")
        return jsonify({"success": True, "message": f"Switched to branch {branch_name}"})
    except Exception as e:
        logging.error(f"Error switching branch: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/list_commits', methods=['GET'])
def list_commits():
    commits = [{"hash": commit.hexsha, "message": commit.message.strip(), "date": commit.committed_datetime} for commit in repo.iter_commits()]
    logging.info("Listed commits for the repository")
    return jsonify(commits)

@app.route('/commit_files', methods=['POST'])
def commit_files():
    data = request.json
    commit_hash = data.get('commit_hash')
    commit = repo.commit(commit_hash)
    files_changed = [item.a_path for item in commit.diff(commit.parents[0])]
    logging.info(f"Files changed for commit {commit_hash}: {files_changed}")
    return jsonify(files_changed)

@app.route('/file_diff', methods=['POST'])
def file_diff():
    data = request.json
    commit_hash = data.get('commit_hash')
    file_path = data.get('file_path')
    commit = repo.commit(commit_hash)
    parent_commit = commit.parents[0]
    diff_text = repo.git.diff(parent_commit.hexsha, commit_hash, file_path)
    logging.info(f"File diff retrieved for {file_path} in commit {commit_hash}")
    return jsonify({"diff": diff_text})

if __name__ == '__main__':
    logging.info("Starting Flask application for GitHub UI")
    app.run(debug=True)
# Basic HTML Template
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Bitbucket UI</title>
    <script>
        function switchBranch() {
            let branch = document.getElementById('branchSelect').value;
            fetch('/switch_branch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ branch: branch })
            }).then(response => response.json()).then(data => alert(data.message));
        }

        function listCommits() {
            fetch('/list_commits').then(response => response.json()).then(commits => {
                let commitList = document.getElementById('commitList');
                commitList.innerHTML = '';
                commits.forEach(commit => {
                    let option = document.createElement('option');
                    option.value = commit.hash;
                    option.text = `${commit.date} - ${commit.message}`;
                    commitList.appendChild(option);
                });
            });
        }

        function listChangedFiles() {
            let commitHash = document.getElementById('commitList').value;
            fetch('/commit_files', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ commit_hash: commitHash })
            }).then(response => response.json()).then(files => {
                let fileList = document.getElementById('fileList');
                fileList.innerHTML = '';
                files.forEach(file => {
                    let option = document.createElement('option');
                    option.value = file;
                    option.text = file;
                    fileList.appendChild(option);
                });
            });
        }

        function showFileDiff() {
            let commitHash = document.getElementById('commitList').value;
            let filePath = document.getElementById('fileList').value;
            fetch('/file_diff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ commit_hash: commitHash, file_path: filePath })
            }).then(response => response.json()).then(data => {
                document.getElementById('diffOutput').innerText = data.diff;
            });
        }
    </script>
</head>
<body>
    <h1>Bitbucket UI</h1>
    <label for="branchSelect">Select Branch:</label>
    <select id="branchSelect" onchange="switchBranch()"></select>
    <button onclick="listCommits()">List Commits</button>
    <br><br>
    <label for="commitList">Select Commit:</label>
    <select id="commitList" onchange="listChangedFiles()"></select>
    <br><br>
    <label for="fileList">Select File:</label>
    <select id="fileList" onchange="showFileDiff()"></select>
    <br><br>
    <pre id="diffOutput"></pre>

    <script>
        fetch('/').then(response => response.text()).then(html => {
            document.getElementById('branchSelect').innerHTML = html;
        });
    </script>
</body>
</html>
"""

with open("templates/index.html", "w") as f:
    f.write(html_template)
