# Corporate Banking Agents - Walkthrough

This project (`C:\Python\BankingAgents`) demonstrates 3 LangGraph-based agents tailored for a Corporate Banking environment.

## Quick Start

The entry point is `main.py`. It uses mock tools to simulate the JBoss/Unix environment.

### 1. Run L1 Support Agent
Diagnoses a server issue. The demo simulates a "Critical OOM" that requires human approval.
```powershell
python C:\Python\BankingAgents\main.py support --scenario oom
```
*Observation*: The agent will diagnose the health, find the OOM log, and then reach the `human_approval` node. In this CLI demo, it will show the interrupt state.

### 2. Run Batch Recovery Agent
Simulates a failed batch job.
*   **Scenario: Network Error** (Auto-Retry)
    ```powershell
    python C:\Python\BankingAgents\main.py batch --scenario network
    ```
    *Result*: Agent classifies it as "Transient" and retries the job.

*   **Scenario: Data Checksum Error** (Escalate)
    ```powershell
    python C:\Python\BankingAgents\main.py batch --scenario data
    ```
    *Result*: Agent classifies it as "Data Quality" and pages support.

### 3. Run Compliance Agent
Audits a feature branch for code quality.
```powershell
python C:\Python\BankingAgents\main.py compliance --branch feature/payment-fix
```
*Result*: Agent fetches the git diff (mocked), finds `System.out.println` violations, and fails the compliance check.

## Project Structure
-   `agents/support.py`: Unix/JBoss diagnostics + HITL.
-   `agents/batch.py`: Autonomous decision making (Retry vs Escalate).
-   `agents/compliance.py`: Code auditing agent.
-   `tools/mocks.py`: Simulates SSH, DB, and JBoss CLI.
