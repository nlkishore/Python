# Clean target repository — analysis and PR plan

**Status:** Target repo created; **PR-1 open** — https://github.com/nlkishore/banking-control-plane/pull/1  
**Date:** 2026-09-12  
**Vehicle it extends:** GitRepoPlan / `repo-consolidated` (archive only), HotFix Case 1+2, PR gate, git-tools  
**Gaps it closes:** **IDP golden path** (one runnable repo with tests, not 26 remotes), **DORA** (HotFix packages land with pytest)  
**Do not:** merge oscarmovies / Eureka / docker-nginx into this repo. Do not treat `repo-consolidated` as the living tree.

**Canvas:** [repo-rationalize-plan.canvas.tsx](C:\Users\nlaxm\.cursor\projects\c-Python-Cursor-mcp-workspace\canvases\repo-rationalize-plan.canvas.tsx)

---

## 1. What we scanned

| Source | Count | What it is |
|--------|-------|------------|
| GitHub `nlkishore` remotes | **26** | Live + learning + dumps |
| Prior hash consolidation | 18 repos, 32 branches, 5708 files | `repo-consolidated`: imported 2379, **deduped 2646**, skipped 683 |
| Local roots | `C:\Python`, `C:\Python-Cursor`, `C:\MyGeneratedProjects`, `C:\Investment`, `C:\all-branch-code` | Working copies overlapping the remotes |

`repo-consolidated` already proved **exact-hash duplicates**. It is **not** a product: it kept empty files, selenium copies, Eclipse metadata, and GEB PowerPoints. The new repo is the opposite: **only tested packages, one copy each**.

---

## 2. Remote disposition (26 GitHub repos)

### A. Target (new) — one living product

| Repo | Action |
|------|--------|
| **`banking-control-plane`** (create, **private**) | Only destination for banking HotFix / PR / binary / testbed Python |

### B. Keep as-is (do not fold in)

| Repo | Why |
|------|-----|
| `turbine-fw-projects` | Large Java/Turbine framework — separate from the Python control plane |
| `Python` | Source of packages until PRs land; then freeze / archive |
| `git-tools` | Source for `hotfix_validation` / `properties_diff` (PR 3) |
| `tdd-screen-extractor` | Later PR if tests exist |
| Investment (`C:\Investment`, not a GitHub dump) | Personal IBKR — never this repo |

### C. Archive / freeze (no new commits; do not copy)

`cursor-projects`, `repo-consolidated`, `eclipse-workspace`, `kishore`, `Java`, `Junit`, `ChatGPT`, `node`, `docker-app-lab`, `agents-from-scratch`, `TestRepo`, `Spring-Scheduler`, `AIBasedDocs`, `robot-testing`

### D. Retire as platform narrative (strangler labs only)

`oscarmovies`, `SpringBootWithEureka`, `SpringBoot`, `spring`, `MicroService`, `docker-nginx`, `techworld-with-nana-container-orchestration-with-kubernetes`, `k8s`

---

## 3. Duplicate code (what not to copy)

Prior scan: **906** filename groups with 2+ copies; **65** Python files duplicated across `Python` branches (`main`, `master`, `GoogleAntiGraviryProjets`, `openRewrite`, `python-cursor`, `Test1`).

### Branch copies of the same script (do not PR)

Same bytes on 6–8 branches: `seleniumTest.py`, `seleniumTest3.py`, `python_selenium1.py`, `Python_selenium.py`, `PropReader.py`, `CommonExcelmethods.py`, `stockDownload.py`, `readcsv.py`, `firstSparkExample.py`, `dataClose.py`, `dataStatistics.py`. One copy in an archive zip is enough.

### Feature clones (pick one canonical)

| Cluster | Copies | Canonical | Drop |
|---------|--------|-----------|------|
| Bitbucket REST client | `hotfix_prep.bitbucket`, `pr_review.scm.bitbucket_server`, `ReleaseControl.clients.bitbucket` | **`release_control.connections`** | `common/connectors.py` ping |
| Bitbucket branch audit | `Bitbucket/branch_auditor.py` vs `BitbucketAudit/branch_auditor.py` (**different hashes**) | Later: one auditor importing `release_control` | The other folder |
| Artifactory latest-build | `ArtifactoryBuildFinder` | **`release_control.clients.artifactory`** | Finder package |
| HotFix filesList | `hotfix_prep`, `hotfix_validation`, HFGenratorAgent (GitHub) | Case 1 = `hotfix_prep`; schema = `hotfix_validation` | HFGenratorAgent |
| JBoss decompose | `jbossmigration/` vs `UnixSxripting/jbossmigration/` (one hash is **empty**) | One non-empty script, only after tests | Empty file, UnixSxripting copy |
| `config_loader.py` | 3 unrelated hashes | Keep inside each **tested** package | `common/config_loader.py` |
| `generate_projects.py` | 2 versions in Java-Projects | Out of scope for this repo | Both |

### Empty / junk hashes

`ML/pfAnalysis.py` and several “deduped” xlsx/log files share the **empty SHA**. Never import.

---

## 4. What is actually tested (eligible for PRs)

| Package | Tests | Local path | PR |
|---------|-------|------------|----|
| `release_control` | **19 passed** | `C:\Python\ReleaseControl` | **PR-1** |
| `hotfix_prep` | **26 passed** | `C:\Python\HotFixAgent` | **PR-1** (same PR: shared remotes + Case 1) |
| `hotfix_validation` / `properties_diff` / `cr_slice_validation` | git-tools tests exist | `repo-consolidated/git-tools` | **PR-3** after they import `release_control` |
| `pr_review` | 1 test (`test_diff_parser`) | `C:\Python-Cursor\Python\pr-code-review-automation` | **PR-4** after Bitbucket client delegates to `release_control` |
| `geb-integration-testbed` | contract tests | `repo-consolidated/.../geb-integration-testbed` | **PR-5** (SLO vehicle) |
| Investment packages | many | `C:\Investment` | **Never this repo** |
| BankingAgents, HFGenratorAgent, ear_agent, connectors.py | missing or mock/GitHub | various | Not until tests + token factories |

Gate for every later PR: `pytest` green in CI; no `*_PASSWORD`; import `release_control.connections` for remotes.

---

## 5. Target repository layout

```
banking-control-plane/          # GitHub private
  README.md
  .github/workflows/test.yml    # pytest per package
  .cursor/rules/                # bitbucket-remote-clients + devops-token-auth
  packages/
    hotfix-prep/                # Case 1
    release-control/            # Case 2
    hotfix-validation/          # PR-3
    pr-review/                  # PR-4
    geb-testbed/                # PR-5
```

One HTTP/config story: `packages/release-control` is the shared remote SDK. Other packages **import** it.

---

## 6. PR sequence (non-duplicate only)

| PR | Branch | Content | CI |
|----|--------|---------|----|
| **0** | `main` | README, .gitignore, workflow stub, rules | workflow exists |
| **1** | `feat/hotfix-release-control` | `hotfix-prep` + `release-control` (already tested) | 26+19 pytest |
| **2** | `feat/ci-matrix` | GitHub Actions matrix both packages | required check |
| **3** | `feat/hotfix-validation` | git-tools validators; delete duplicate schema copies | pytest |
| **4** | `feat/pr-review-uses-release-control` | PR gate; Bitbucket client = shared factory | pytest |
| **5** | `feat/geb-testbed` | GEB contract tests (SLO slice) | pytest |

No PR for selenium labs, oscarmovies, empty `pfAnalysis.py`, `common/connectors.py`, or Investment.

---

## 7. After PR-1

- Stop adding features under `C:\Python` root as loose scripts.
- `nlkishore/Python` stays readable until PR-5; then mark README: “active work is banking-control-plane”.
- `repo-consolidated` remains the **hash archive** (provenance CSVs), not a clone target.

---

## 8. Open confirmation (does not block PR-1)

1. GitHub name `banking-control-plane` and **private** visibility.
2. Whether `turbine-fw-projects` ever gets a sibling `geb-portal` Java repo (not this Python plane).
