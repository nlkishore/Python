# Bitbucket Branch Auditor

A utility to audit release branches before production cut-over. It ensures that critical fixes from the **Main Release Branch** have been merged into the specific **Chain Request (CR)** branches.

## Problem Statement
In a multi-branch release strategy, hotfixes often land on the Main Branch (e.g., `Release-A`). If a fast-tracked CR branch (e.g., `Release-CR-B`) is cut earlier, it might miss subsequent fixes from Main. This tool detects such "Deltas".

## Usage

### 1. Configure Audits (`audit_config.json`)
Define the relationships between Source (Main) and Targets (CRs).

```json
[
  {
    "country": "Country-B",
    "project": "BANK_SG",
    "repository": "payment-gateway",
    "source_branch": "refs/heads/release/branch-A",
    "target_branches": [
      "refs/heads/release/branch-B",
      "refs/heads/release/branch-C"
    ]
  }
]
```

### 2. Configure Credentials (`../common/config.ini`)
Ensure your Bitbucket URL and User/Token are set in the common configuration.

```ini
[bitbucket]
url=https://bitbucket.bank.internal
user=audit_bot
token=your_access_token
```

### 3. Run the Auditor
```powershell
python branch_auditor.py
```

### 4. Output
*   **HTML Report** (`audit_report_YYYYMMDD.html`): Summary view.
*   **Excel Report** (`audit_report_YYYYMMDD.xlsx`): Detailed view with **Hyperlinks** to Bitbucket commits for easy review.
