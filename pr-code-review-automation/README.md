# PR Code Review Automation (Python)

Enterprise **Bitbucket Server / Data Center** pull-request pipeline: clone PR workspace, **changed-line report** (for reconciling findings with new code), **Maven compile**, optional **SpotBugs** (+ FindSecBugs), **Semgrep** (OWASP packs), **PMD**, **OWASP Dependency-Check**, **SonarScanner** — plus configurable **IntelliJ / Eclipse** paths for manual review with **SonarLint**.

## Quick start

```powershell
cd C:\Python-Cursor\pr-code-review-automation
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
copy config\settings.example.yaml config\settings.yaml
# Edit config\settings.yaml — set BITBUCKET_TOKEN (and optional SONAR_* env vars)
$env:BITBUCKET_TOKEN = "your-pat"
python -m pr_review run --config config/settings.yaml
```

CLI (if `Scripts` is on `PATH`): `pr-review run --config config/settings.yaml`

## Configuration (`config/settings.example.yaml`)

| Section | Purpose |
|--------|---------|
| **bitbucket** | `server_url`, `token` (`${BITBUCKET_TOKEN}`), `username` (default `x-token-auth`), `project_key`, `repository_slug`, `pull_request_id`, `api_path_prefix`, `verify_ssl` |
| **repository** | `clone_url_override` (optional), `pr_ref_strategy`: `from` \| `merge` |
| **paths** | `git`, `maven` (full path to `mvn` / `mvn.cmd`), `java_home`, `workspace_root` |
| **spotbugs** | `home` (SpotBugs install dir or executable), `findsecbugs_plugin_jar`, `enabled` |
| **semgrep** | `executable`, `extra_args` (e.g. `p/java`, `p/owasp-top-ten`), `enabled` |
| **pmd** | `executable`, `rulesets` (error-prone / security for NPE-style issues), `enabled` |
| **dependency_check** | `executable`, `enabled` |
| **sonarqube** | `scanner_path`, `host_url`, `token`, `project_key`, `enabled` |
| **ide** | `intellij_path`, `eclipse_path`, `print_open_hints` |
| **pipeline** | Maven args, timeouts |
| **reports** | `output_subdir` under workspace |

### SonarLint vs SonarScanner

- **SonarLint** runs **inside** Eclipse/IntelliJ; there is no supported headless SonarLint CLI equivalent for the same UX.
- This tool configures **`sonar-scanner`** against your **SonarQube** server so rules can align with **connected mode** / quality profiles used with SonarLint in the IDE.
- Use **`ide.intellij_path`** / **`ide.eclipse_path`** to open the cloned workspace for interactive SonarLint review after the run.

## Outputs (under `<workspace_root>/<project>_<repo>_PR<id>/pr-review-reports/`)

| File | Description |
|------|-------------|
| `changed-lines.json` | Per-file **added line ranges** (post-image) for PR reconciliation |
| `compile-report.json` | Maven result + parsed compiler issues |
| `run-summary.json` | Full run metadata |
| `summary.html` | Human-readable summary |
| `spotbugs-report.xml` | If SpotBugs enabled |
| `semgrep.sarif` | If Semgrep enabled |
| `pmd-report.xml` | If PMD enabled |
| `sonar-project.properties` | If SonarScanner used (under reports dir) |

## Documentation

- **[Approach document](docs/APPROACH-PYTHON-PR-CODE-REVIEW.md)** — architecture, Bitbucket-focused configuration, IDE/Sonar notes, agentic AI follow-up.

## Requirements

- Python **3.10+**
- Git, JDK, Maven on `PATH` (or absolute paths in config)
- Optional: SpotBugs, Semgrep, PMD, Dependency-Check, SonarScanner binaries as configured

## Project layout

```
pr-code-review-automation/
  config/settings.example.yaml
  docs/
  src/pr_review/
    cli.py
    pipeline.py
    config/
    scm/bitbucket_server.py
    git_ops.py
    diff_parser.py
    build/maven_runner.py
    analyzers/
    reports/templates/
  tests/
```

## License

Apache-2.0 (see `pyproject.toml`).
