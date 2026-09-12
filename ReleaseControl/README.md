# Release Control (Case 2)

Reusable Python modules so PR files, HotFix `filesList`, Jenkins/Artifactory binaries, and UAT vs Production binary deltas can be **reconciled without a local git clone**.

**Plan:** `C:\MyGeneratedProjects\User-Prompts-Documentation\RELEASE-CHANGE-RECONCILE-PLAN.md`  
**Extends:** `C:\Python\HotFixAgent` (Case 1 — generate `filesList.txt`). This package **reads and proves**; it does not apply HotFix.

## Why this exists

Thirty-plus one-off scripts each reimplemented Bitbucket/Jenkins/Artifactory HTTP. This package is **one HTTP client + eight modules + one CLI**. A new check is a function, not a new program folder.

## Setup

```bash
cd C:\Python\ReleaseControl
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Tokens stay in `.env` (`BITBUCKET_TOKEN`, `JENKINS_TOKEN`, `ARTIFACTORY_TOKEN`). Login passwords are rejected. There is no local product repository option.

## Commands

```bash
release-control pr-files --project BANK --slug core-app --pr-id 1842
release-control hotfix-scan --project BANK --slug hotfix-sg --branch hotfix/sg
release-control jenkins-artifact --job geb-sg-release --build lastSuccessful
release-control inventory --archive .\tmp\app.ear
release-control reconcile --pr-json pr.json --hotfix-json hf.json --exceptions config\exceptions.yaml
```

`reconcile` exit `0` for `PASS` or `REVIEW`, `1` for `FAIL`. Apply to control still requires HITL + digest pin.

## Shared config and remotes

Every new Bitbucket / Jenkins / Artifactory feature **imports** these — it does not copy them:

```python
from release_control.connections import (
    load_settings, bitbucket_client, jenkins_client, artifactory_client,
)
```

Cursor rule: `.cursor/rules/bitbucket-remote-clients.mdc` (also in `mcp_workspace`, `Python-Cursor`, `MyGeneratedProjects`).

## Modules

| Module | Responsibility |
|--------|----------------|
| `http.RestClient` | Only HTTP. Retry-ready timeouts, secret redaction, SHA-256 on download |
| `clients.bitbucket` | PR changes, compare, raw `filesList`, browse, stream binary |
| `clients.jenkins` | SUCCESS gate, Artifactory URI from JSON |
| `clients.artifactory` | Latest numeric build, download |
| `mapping.paths` | `.java` → `WEB-INF/classes/...class` (keep in sync with `hotfix_prep`) |
| `inventory.fileslist` | Parse YAML `filesList.txt` + PR ids |
| `inventory.archives` | EAR/WAR/ZIP members + nested one level |
| `reconcile` | Set equality after `exceptions.yaml` |

## Tests

```bash
pytest
```

HTTP is mocked. Archive tests use in-memory zip files.
