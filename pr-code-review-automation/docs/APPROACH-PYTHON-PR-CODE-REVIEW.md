# PR-Based Code Review Automation — Python-First Approach

**Audience:** Enterprise Java web application teams, code reviewers, DevSecOps  
**Decision:** All orchestration, reporting, reconciliation, and (where feasible) analysis **glue** is implemented in **Python**. External **Java-native** analyzers and build tools are invoked as **subprocesses** from Python.

**Status:** **v0.1 implemented** under `C:\Python-Cursor\pr-code-review-automation\` (Bitbucket Server, Maven, analyzers, reports). **Agentic AI** layer remains a follow-up.

---

## 1. Objectives

| # | Objective |
|---|-----------|
| 1 | After a developer opens a **Pull Request**, automate checkout of **PR-scoped code** (by PR ID). |
| 2 | Produce a **per-file changed-line report** (line numbers in the post-PR tree) to reconcile static-analysis findings with **new vs existing** code. |
| 3 | **Compile** the project using the **same** Maven/Gradle setup and **local/corporate** dependency caches as developer machines. |
| 4 | Emit a **compilation report** on failure (file, line, message where parseable). |
| 5 | After successful compile (or partial success strategy), run **security** (OWASP-aligned), **reliability** (e.g. NPE-style), and **quality** checks; aggregate into **unified reports**. |
| 6 | Optional later: **agentic AI** layer for triage, explanations, and fix suggestions — still orchestrated from Python. |

---

## 2. Why Python for Everything (Orchestration Layer)

- **Single language** for: Git/PR APIs, diff parsing, subprocess management (Maven, Gradle, SpotBugs, Semgrep, etc.), SARIF/JSON merge, HTML/PDF reports, CLI, and future LLM agents.
- **Fast iteration** and rich libraries (`httpx`/`requests`, `subprocess`, `pathlib`, `jinja2`, `pyyaml`, `pydantic`).
- **Enterprise fit:** Python is standard for CI/CD and security pipelines; Java remains the **application** language; analyzers stay **JVM-based** where they are strongest.

**Clarification:** “All activities in Python” means the **control plane** is Python. **Compilation** is still `javac` via Maven/Gradle; **bytecode analyzers** remain Java tools — Python **invokes** them and **parses** outputs.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Python CLI / Agent (orchestrator + future LLM reasoning)        │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐
│ Bitbucket       │  │ git CLI         │  │ subprocess:          │
│ Server REST API │  │ fetch/checkout  │  │ mvn, spotbugs,       │
│                 │  │                 │  │ semgrep, pmd,        │
│                 │  │                 │  │ dep-check, sonar     │
└─────────────────┘  └─────────────────┘  └──────────────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              ▼
         ┌────────────────────────────────────────────┐
         │  Python: diff → line ranges per file       │
         │  Python: merge SARIF/XML → unified model   │
         │  Python: tag findings “in_pr_diff”         │
         │  Python: HTML / SARIF / JSON reports       │
         └────────────────────────────────────────────┘
```

---

## 4. Phased Workflow

### Phase 4.1 — Inputs & configuration (implemented: `config/settings.example.yaml`)

All settings are **YAML** with `${ENV_VAR}` substitution (e.g. `${BITBUCKET_TOKEN}`).

| Group | Keys (summary) |
|-------|----------------|
| **bitbucket** | `server_url`, `token`, `username` (default `x-token-auth` for PAT), `project_key`, `repository_slug`, `pull_request_id`, `api_path_prefix` (`/rest/api/latest`), `verify_ssl` |
| **repository** | `clone_url_override`, `pr_ref_strategy` (`from` \| `merge`) for `refs/pull-requests/{id}/…` |
| **paths** | `git`, `maven` (absolute path to `mvn` / `mvn.cmd` on Windows), `java_home`, `workspace_root` |
| **spotbugs** | `home` (install dir or `spotbugs.bat`), `findsecbugs_plugin_jar`, `enabled` |
| **semgrep** | `executable`, `extra_args` (e.g. `p/java`, `p/owasp-top-ten`), `enabled` |
| **pmd** | `executable`, `rulesets` (e.g. `category/java/errorprone.xml`, `category/java/security.xml`), `enabled` — **NPE-style / reliability** patterns |
| **dependency_check** | `executable`, `enabled` — **OWASP** dependency analysis |
| **sonarqube** | `scanner_path`, `host_url`, `token`, `project_key`, `enabled` — aligns with **SonarQube** rules used alongside **SonarLint** in IDE |
| **ide** | `intellij_path`, `eclipse_path`, `print_open_hints` — **SonarLint** runs inside IDE; paths support **manual** open of cloned repo |
| **pipeline** | `maven_compile`, `maven_compile_args`, timeouts |
| **reports** | `output_subdir` under each PR workspace |

### Phase 4.2 — Fetch PR and materialize workspace

1. Call platform **REST API** to resolve:
   - PR head SHA, base SHA, merge ref (if reviewing “as merged”).
   - List of **changed files** (optional early exit for docs-only PRs).
2. **Git** (`subprocess`):
   - Clone via authenticated URL (`x-token-auth:TOKEN` embedded for Bitbucket Server HTTPS).
   - `git fetch origin refs/pull-requests/{id}/from:refs/remotes/origin/pr-from`
   - Fetch target branch `refs/heads/{toBranch}:refs/remotes/origin/pr-target` for merge-base.
   - Checkout **`fromRef.latestCommit`** from the PR API.
3. **IDE project:** Do **not** hand-craft IntelliJ/Eclipse metadata. Open folder containing **`pom.xml`** or **`build.gradle`** — document that reviewers use **Import Maven/Gradle project**. Optional Python step: validate presence of build descriptors.

### Phase 4.3 — Changed-lines report (reconciliation)

**Goal:** For each file in the PR, know which **line numbers (in the PR version of the file)** were **added or modified**.

**Implementation (Python):**

1. Run `git diff <base>...<head>` (three-dot) or platform-provided **patch**.
2. Parse **unified diff** in Python:
   - Track hunks: `@@ -old_start,old_len +new_start,new_len @@`
   - For each **added** line (`+` not `+++`), map to **new file line number**.
3. Output **structured report** (JSON/CSV), e.g.:

```json
{
  "pull_request_id": 123,
  "base_sha": "...",
  "head_sha": "...",
  "files": [
    {
      "path": "src/main/java/com/acme/OrderService.java",
      "change_type": "M",
      "added_line_ranges": [[12, 18], [45, 45]],
      "added_lines_flat": [12,13,14,15,16,17,18,45]
    }
  ]
}
```

4. **Reconciliation rule:** A finding at `(file, line)` is **`in_pr_diff: true`** iff `line` is contained in `added_line_ranges` (post-image lines). Renames: resolve `old_path` → `new_path` from diff.

**Deliverable:** `reports/changed-lines.json` (and optional human-readable `.md`).

### Phase 4.4 — Compilation

**Implementation (Python):**

1. **Implemented:** Maven only (`pom.xml` expected). Gradle can be added similarly.
2. Run non-interactive compile, e.g.:
   - Maven: `mvn -q -DskipTests compile` (configurable args).
   - *Future:* `./gradlew compileJava`.
3. Capture **exit code**, **stdout**, **stderr**.
4. **Parse** compiler errors (regex/heuristics for `file:line: error:` patterns) into a list of objects.
5. Write **`reports/compile-report.json`**; on failure, still proceed to **source-only** tools if configured (e.g. PMD/Semgrep on changed files).

**Dependencies:** Rely on **machine-local** `~/.m2`, Gradle cache, and **corporate** `settings.xml` / `init.gradle` — document as **prerequisites**.

### Phase 4.5 — Static analysis (post-compile preferred)

| Concern | Example tools | Invoked by Python |
|--------|----------------|-------------------|
| OWASP dependency risks | OWASP Dependency-Check | `dependency-check.sh` / CLI |
| Security bug patterns | SpotBugs + **FindSecBugs** JAR (`-pluginList`) | **Standalone** SpotBugs CLI + Maven `dependency:build-classpath` |
| Policy / injection / XSS | Semgrep (Java + OWASP rules) | `semgrep` CLI |
| Null / style / complexity | PMD, Checkstyle | CLI or Maven plugin |
| Sonar / SonarLint alignment | **SonarScanner** + SonarQube server | **Not** SonarLint CLI (IDE-only); server analysis complements IDE |

**Outputs:** Prefer **SARIF** for interchange; Python normalizes to internal model.

### Phase 4.6 — Unified report & PR reconciliation

1. Ingest all tool outputs (SARIF, XML, plain text).
2. For each finding: attach `file`, `line`, `rule_id`, `severity`, **`in_pr_diff`** (from Phase 4.3).
3. Generate:
   - **`reports/unified-findings.json`**
   - **`reports/review-summary.html`** (Jinja2 template)
   - Optional **`reports/unified.sarif`** for GitHub/GitLab upload.

---

## 5. Security & Operations

- **Secrets:** Tokens only via env (e.g. `BITBUCKET_TOKEN`, `SONAR_TOKEN`) or enterprise secret manager; never commit `config/settings.yaml` with secrets (gitignored template flow).
- **Least privilege:** Bitbucket **HTTP access token** / PAT with **read** access to project/repo and pull requests.
- **Sandbox:** Run compile and scanners in **isolated workdir** per PR; disk quotas and timeouts.
- **Supply chain:** Pin Python deps (`requirements.txt` + hashes or Poetry lock); pin scanner versions in CI image.

---

## 6. Project Layout (as implemented)

Repository: `C:\Python-Cursor\pr-code-review-automation\`

```
pr-code-review-automation/
  config/
    settings.example.yaml
  docs/
    APPROACH-PYTHON-PR-CODE-REVIEW.md
  src/pr_review/
    __main__.py
    cli.py                 # Typer: pr-review run / version
    pipeline.py            # orchestration
    config/
      schema.py            # Pydantic settings
      loader.py            # YAML + ${ENV}
    scm/
      bitbucket_server.py  # REST: PR metadata + changed paths
    git_ops.py             # clone, fetch PR refs, merge-base, diff
    diff_parser.py         # unified diff → added line ranges
    build/
      maven_runner.py
    analyzers/
      spotbugs_runner.py   # + optional FindSecBugs
      semgrep_runner.py
      pmd_runner.py
      dependency_check_runner.py
      sonar_runner.py
    reports/
      writer.py
      templates/summary.html.j2
  tests/
  pyproject.toml
  README.md
```

**Future:** `src/pr_review/agents/` for **agentic AI** (consume `run-summary.json`, `changed-lines.json`, tool SARIF/XML).

### 6.1 SonarLint, Eclipse, and IntelliJ

- **SonarLint** is designed for **in-IDE** analysis; the enterprise workflow is: run this pipeline for **compile + central scanners**, then open the same workspace in **IntelliJ** or **Eclipse** (paths in `ide.*`) to apply **SonarLint** with **connected mode** to SonarQube where applicable.
- Configured **`intellij_path`** / **`eclipse_path`** are printed as **hints** after a run (`ide.print_open_hints`); they do not launch the IDE automatically unless extended later.

---

## 7. Agentic AI Extension (Next Phase)

After the **deterministic** pipeline is stable:

- **Agents** (Python + LLM API): read `unified-findings.json` + relevant **file snippets** + **changed-lines** context; produce ranked explanations, false-positive likelihood, and suggested patches.
- **Guardrails:** No auto-merge without human approval; redact secrets from prompts; use **only** PR-scoped paths.

This document **does not** implement agents; it **reserves** the `agents/` module and defines **inputs/outputs** the agent will consume.

---

## 8. Prerequisites (Runner Machine)

| Component | Notes |
|-----------|--------|
| Python | 3.11+ recommended |
| Git | In `PATH` |
| JDK | Same major version as project |
| Maven / Gradle | As required by repo |
| Optional CLIs | `semgrep`, OWASP Dependency-Check, `sonar-scanner` |
| Network | Access to corporate Nexus/Artifactory + SCM API |

---

## 9. Success Criteria

- [x] PR ID → reproducible checkout for **Bitbucket Server** (Git + REST).
- [x] **`changed-lines.json`** generated (basis for **`in_pr_diff`** on merged findings — merge step can be extended).
- [x] Maven **compile** with **pass/fail** and **compile-report.json**.
- [x] Optional **OWASP-oriented** (Semgrep packs, FindSecBugs, Dependency-Check) and **reliability** (PMD error-prone, SpotBugs) via Python subprocess wrappers.
- [x] **HTML + JSON** summary (`summary.html`, `run-summary.json`).
- [ ] **Unified SARIF** merge + per-finding `in_pr_diff` flag (next iteration).
- [ ] **Agentic AI** triage layer.

---

## 10. Revision History

| Version | Date | Notes |
|---------|------|--------|
| 1.0 | 2026-03-09 | Initial Python-first approach |
| 1.1 | 2026-03-09 | Bitbucket Server config, Maven/SpotBugs/Semgrep/PMD/Dep-Check/SonarScanner/IDE paths; implemented package `pr_review`; doc aligned with repo |

---

*End of document.*
