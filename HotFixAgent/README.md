# HotFix Prep (Case 1)

Automates the step after a Bitbucket Pull Request **merges** to a market **release** branch: generate `filesList.txt` and `buildScripts.sh`, commit **both in one commit** to that market’s **HotFix** branch, and let existing HotFix CI produce the incremental zip.

Plan: `C:\MyGeneratedProjects\User-Prompts-Documentation\BITBUCKET-HOTFIX-PR-MERGE-AUTOMATION-PLAN.md`

**Case 2 (read and prove, no local clone):** `C:\Python\ReleaseControl` reconciles PR files, this HotFix list, Jenkins/Artifactory binaries, and UAT vs Production deltas. Plan: `C:\MyGeneratedProjects\User-Prompts-Documentation\RELEASE-CHANGE-RECONCILE-PLAN.md`.

## Setup

```bash
cd C:\Python\HotFixAgent
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Edit `config/markets.yaml` with real project keys, slugs, and branch names. Put Bitbucket credentials in `.env` only.

## Dry-run a merged PR (no HotFix commit)

```bash
hotfix-prep process --project BANK --slug core-app --pr-id 1842 --dry-run
```

## Live webhook

Bitbucket Server webhook: event `pr:merged`, URL `http://<host>:8080/webhooks/bitbucket/pr-merged`, secret = `WEBHOOK_SECRET`.

```bash
hotfix-prep serve
```

`GET /health` is the liveness check. `POST /v1/process` replays a PR (`project`, `slug`, `pr-id`, optional `dry_run`).

## Tests

```bash
pytest
```

## Notes

- Placeholder markets: SG, IN, HK, MY, TH, ID, VN — replace with real names.
- Java sources map to `WEB-INF/classes/...class`. Tests, docs, and `pom.xml` are skipped. Unmapped paths fail the job; nothing is committed.
- Filenames default to `filesList.txt` and `buildScripts.sh` (configurable in `markets.yaml`).
- Legacy helpers remain under `scripts/` (`prepare_hotfix.py`, `validate_hotfix.py`).
