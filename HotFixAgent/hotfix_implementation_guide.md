# HotFix Implementation & Automation Guide

## Overview
This document outlines the workflow for managing Change Requests (CR) that lead to HotFixes. It includes manual steps and proposed automation scripts for:
1.  **Development**: Branching & PRs.
2.  **HotFix Prep**: Generating file lists from PRs.
3.  **Validation**: Verifying artifacts and patching EARs.

---

## Part 1: Development Workflow

### 1. Branch Creation
*   **Source**: `TargetBranch` (e.g., `release/1.0`, `master`)
*   **Naming Convention**: `feature/CR-<ID>-<Description>`
*   **Command**:
    ```bash
    git fetch origin
    git checkout -b feature/CR-1234-fix-login origin/TargetBranch
    ```

### 2. Development & Commit
*   Developer makes changes.
*   **Compile**: Run local build (e.g., `mvn clean install` or `ant build`).
*   **Commit**:
    ```bash
    git add .
    git commit -m "CR-1234: Fixed login issue"
    git push origin feature/CR-1234-fix-login
    ```

### 3. Automated PR Creation
**Question**: Can PR raising be automated?
**Answer**: **YES**. Use the Bitbucket/GitHub REST API or CLI.

**Script Approach (Python/Requests)**:
See `scripts/raise_pr.py` (Drafted below).
*   **Inputs**: Source Branch, Target Branch, Title, Reviewers.
*   **Action**: POST to repository API.

---

## Part 2: Release & Build Wait
*   **Merge**: PR is approved and merged to `TargetBranch`.
*   **Wait**: The CI/CD pipeline builds the `TargetBranch`. (Duration: ~2 Hours).
*   *Automation Tip*: You can poll the Jenkins/Bamboo API to check for build completion status instead of manual waiting, but often a simple notification hook is enough.

---

## Part 3: HotFix triggering (The Tricky Part)

### 1. Generate File List from PR `fileList.txt`
We need to identify exactly which files changed in the PR to package them for the existing EAR.

**Command (Git)**:
```bash
# Get list of changed files between Merge Commit and its Parent
# Or if you have the feature branch:
git diff --name-only origin/TargetBranch...origin/feature/CR-1234-fix-login > fileList.txt
```
*   **Filtering**: You might need to filter only `.class` or source files and map them to the compiled output path.

### 2. Prepare HotFix Branch
*   **Switch Context**: Checkout the `HotFix_Branch` (e.g., `hotfix/release-1.0`).
*   **Commit Metadata**:
    *   Update `buildScript.sh` (Set `HF_NUMBER=1234`, `TARGET_BRANCH=...`).
    *   Add `fileList.txt`.
*   **Trigger**: Pushing these changes usually triggers the specific HotFix build job.

---

## Part 4: Validation & Patching

### 1. Download & Validate (Automated)
After the HotFix build (30m - 1h), download the artifact.

**Validation Logic**:
1.  Unzip `HotFix.zip`.
2.  Read `fileList.txt` (source of truth).
3.  **Check**: Does every file in `fileList.txt` exist in the unzipped folder?
4.  **Report**: Pass/Fail.

### 2. Apply HotFix to EAR
**Scenario**: You have `Application.ear`. You need to inject the files from `HotFix.zip`.

**Workflow**:
1.  Explode `Application.ear` (it is just a ZIP).
2.  Copy/Overlay files from `HotFix` folder into `Exploded_EAR`.
3.  Re-package `Application.ear` (optional, or deploy exploded).

**Command**:
```bash
# Update existing archive
jar uf Application.ear -C HotFix/ .
```

---

## Suggested Automation Scripts

### A. Python Script for File List & HotFix Commit
(See provided file `HotFixAgent/scripts/prepare_hotfix.py`)

### B. Python Script for Validation
(See provided file `HotFixAgent/scripts/validate_hotfix.py`)
