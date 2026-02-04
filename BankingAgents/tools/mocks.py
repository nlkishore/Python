import time
import random

class MockTools:
    @staticmethod
    def ssh_execute(command: str, host: str):
        """Simulates executing a command on a remote Unix server."""
        print(f"[SSH {host}] Executing: {command}")
        time.sleep(1) # Simulate network lag
        
        if "top" in command:
            return "Load Average: 0.45, 0.60, 1.02\nPID USER PR NI VIRT RES SHR S %CPU %MEM TIME+ COMMAND\n1234 jboss 20 0 10g 4g 20m S 1.2 50.0 100:00 java"
        
        if "grep" in command and "OutOfMemory" in command:
            # Simulate finding an error only if specifically asked for OOM
            return "2026-02-04 03:00:12 ERROR [org.jboss.as.server] (ServerService Thread Pool -- 82) java.lang.OutOfMemoryError: Java heap space"
        
        if "grep" in command and "Timeout" in command:
             return "2026-02-04 03:05:00 ERROR [com.bank.batch] Connection timed out connecting to DB_PROD_1"

        if "restart" in command:
            return "Stopping JBoss... Done.\nStarting JBoss... Done.\nProcess ID: 5678"
            
        return "Command executed successfully. No specific output."

    @staticmethod
    def db_query(query: str):
        """Simulates querying a database."""
        print(f"[DB] Executing: {query}")
        time.sleep(0.5)
        
        if "status='PENDING'" in query:
            # Simulate verifying a batch job state
            return [{"count": 0}] # No pending records, maybe it crashed?
            
        if "job_log" in query:
             return [{"status": "FAILED", "error": "DataIntegrityViolation: Null value in column 'AMOUNT'"}]

        return []

    @staticmethod
    def read_file(path: str):
        """Simulates reading a log file."""
        print(f"[FS] Reading: {path}")
        return "2026-02-04 03:00:00 INFO  Batch Started\n2026-02-04 03:01:00 ERROR Validation Failed for Row 10023: Amount cannot be negative."

    @staticmethod
    def bitbucket_diff(branch: str):
        """Simulates getting a git diff."""
        print(f"[Bitbucket] Fetching diff for {branch}...")
        return """
        + System.out.println("Debug password: " + password);
        + // TODO: Fix this later
        + public void processPayment() { ... }
        """
