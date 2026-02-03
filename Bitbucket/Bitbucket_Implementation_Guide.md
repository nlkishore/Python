# Implementation Guide: Bitbucket Branch Integrity & Diff Report

This guide provides a comprehensive approach to managing multi-country source code in Bitbucket, ensuring that critical fixes are not missed across branches and generating periodic integrity reports.

## 1. Context & Challenge

In a multi-country setup with fragmented branches (e.g., `feature-countryA`, `hotfix-countryB`), it is common for:
- A hotfix applied to a production branch to be forgotten and not merged back to `develop`.
- Parallel feature branches to drift significantly.

**Goal**: A report listing unique commit IDs in specific branches that are *missing* from their target integration branches.

## 2. Directory Structure Setup

Ensure your automation environment is set up as follows:

```
C:\Python\Bitbucket\
    ├── Bitbucket_Implementation_Guide.md  # This file
    ├── branch_auditor.py                  # The automation script
    ├── config.json                        # Configuration for branches/countries
    └── reports\                           # Output folder for HTML reports
```

## 3. Implementation Steps

### Step 1: Install Dependencies

You will need Python libraries to interact with Bitbucket and handle data.

```bash
pip install atlassian-python-api pandas jinja2
```

### Step 2: Configuration (`config.json`)

Define your Country-to-Branch mapping rules. This allows the script to know *what* to compare.

```json
{
  "bitbucket_url": "https://your-bitbucket-server.com",
  "project": "GLOBAL_APP",
  "repo": "core-backend",
  "countries": [
    {
      "name": "India",
      "prod_branch": "master-in",
      "develop_branch": "develop-in",
      "hotfix_pattern": "hotfix/in/*"
    },
    {
      "name": "Singapore",
      "prod_branch": "master-sg",
      "develop_branch": "develop-sg",
      "hotfix_pattern": "hotfix/sg/*"
    }
  ]
}
```

### Step 3: The Automation Logic (`branch_auditor.py`)

Create a Python script to communicate with the Bitbucket API.

#### Key Logic:
1.  **Identify Comparison Pairs**: For each country, compare `hotfix/xxx` -> `develop`.
2.  **Fetch Commits**: Use `GET /rest/api/1.0/projects/{project}/repos/{repo}/commits?until={source}&since={target}`.
    *   This API endpoint returns commits reachable from `source` but NOT `target`.
3.  **Filter**:
    *   Ignore Merge Commits (usually not content changes).
    *   (Advanced) Check for "Cherry Picked" commits by comparing commit messages or patch IDs if IDs differ.

#### Sample Code Structure

```python
import json
import csv
from atlassian import Bitbucket

def get_missing_commits(bb, project, repo, source_branch, target_branch):
    """
    Returns list of commits present in source but missing in target.
    """
    try:
        # Get diff/commits (commits in source NOT in target)
        commits = bb.get_commits(project, repo, branch=source_branch, exclude=target_branch)
        
        missing = []
        for commit in commits:
            # Filter out merge commits if needed (parents > 1)
            if len(commit['parents']) == 1:
                missing.append({
                    'id': commit['id'],
                    'author': commit['author']['name'],
                    'message': commit['message'],
                    'date': commit['authorTimestamp']
                })
        return missing
    except Exception as e:
        print(f"Error comparing {source_branch} -> {target_branch}: {e}")
        return []

def generate_report(data):
    # Use Pandas/Jinja2 to create a rich HTML report
    # Columns: Country, Source Branch, Target Branch, Missing Commit ID, Author, Message
    pass

def main():
    # Load Config
    with open('config.json') as f:
        config = json.load(f)
        
    bb = Bitbucket(
        url=config['bitbucket_url'],
        username='<USER>',
        password='<TOKEN>'
    )
    
    report_data = []
    
    for country in config['countries']:
        # 1. Check Hotfixes vs Develop
        # Logic to find actual hotfix branches matching pattern...
        hotfix_branches = ['hotfix/in/login-fix'] # (Mock list, actually fetch via API)
        
        for hf in hotfix_branches:
            missing = get_missing_commits(bb, config['project'], config['repo'], hf, country['develop_branch'])
            for m in missing:
                report_data.append({
                    'Country': country['name'],
                    'Branch': hf,
                    'MissingIn': country['develop_branch'],
                    'Commit': m['id'],
                    'Message': m['message']
                })
                
    # Save Report
    keys = report_data[0].keys()
    with open('C:\\Python\\Bitbucket\\reports\\audit.csv', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(report_data)

if __name__ == "__main__":
    main()
```

## 4. Operationalizing

1.  **Schedule**: Run this script daily via Jenkins or Windows Task Scheduler.
2.  **Review**: Team Leads review the CSV/HTML report.
3.  **Action**:
    *   If a commit is listed, it means it is **Pending Merge**.
    *   Developer must merge `hotfix` -> `develop`.
    *   Once merged, the next run will show 0 missing commits.

## 5. Handling Cherry-Picks (Advanced)

If you use `git cherry-pick`, the Commit ID changes. The simple "Missing Commit" logic will flag these as checks even if code is present.

**Enhancement**:
- Maintain a database/hash of "Subject + AuthorDate".
- If a "missing" commit matches a commit in the target branch by Subject/Date, treat it as "pseudo-merged" and exclude from report.

---
**Saved to**: `C:\Python\Bitbucket\`
```
