import argparse
import sys
import os

# Ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.support import support_agent
from agents.batch import batch_agent
from agents.compliance import compliance_agent

def run_support(scenario):
    print(f"\n--- Running Support Agent (Scenario: {scenario}) ---")
    initial_state = {
        "messages": [], 
        "server_host": "unix-prod-01",
        "action_plan": "",
        "logs": "",
        "issue_detected": ""
    }
    
    # We cheat slightly to ensure mocks return the right scenario
    # In a real app, the mock tools would read env vars or arguments
    # here we assume the mock tools logic handles the input strings
    
    events = support_agent.stream(initial_state)
    for event in events:
        for node, values in event.items():
            print(f"[{node.upper()}]: {values['messages'][-1]}")
            
            # Simulated Human Input
            if node == "human_approval" and "restart" in values['messages'][0]:
                 # In a stream, we can't easily inject input unless we break loop or use interrupt
                 # Since we used `interrupt` in the agent code, LangGraph expects us to handle the resumption
                 # For this simple CLI demo, we can just print the interrupt.
                 pass

def run_batch(scenario):
    print(f"\n--- Running Batch Agent (Scenario: {scenario}) ---")
    
    # scenario mapping to error types handled by mock
    error_type = "Connection timed out" if scenario == "network" else "DataIntegrityViolation"
    
    initial_state = {
        "messages": [],
        "job_id": "JOB_123",
        "error_type": error_type, # Pre-seeding for the simpler mock logic
        "retry_count": 0
    }
    
    events = batch_agent.stream(initial_state)
    for event in events:
        for node, values in event.items():
             print(f"[{node.upper()}]: {values['messages'][-1]}")

def run_compliance(branch):
    print(f"\n--- Running Compliance Agent (Branch: {branch}) ---")
    initial_state = {
        "messages": [],
        "branch_name": branch,
        "diff_content": "",
        "violations": []
    }
    
    events = compliance_agent.stream(initial_state)
    for event in events:
         for node, values in event.items():
             print(f"[{node.upper()}]: {values['messages'][-1]}")

def main():
    parser = argparse.ArgumentParser(description="Corporate Banking Agents Demo")
    parser.add_argument("agent", choices=["support", "batch", "compliance"], help="Which agent to run")
    parser.add_argument("--scenario", default="oom", help="For support/batch: oom, network, data")
    parser.add_argument("--branch", default="feature/payment-fix", help="For compliance: branch name")
    
    args = parser.parse_args()
    
    if args.agent == "support":
        # Note: The 'interrupt' handling in CLI is complex. 
        # For this demo, we will just show it reaching the interrupt state.
        print("Note: Support agent uses 'interrupt' which pauses execution in this CLI demo.")
        run_support(args.scenario)
        
    elif args.agent == "batch":
        run_batch(args.scenario)
        
    elif args.agent == "compliance":
        run_compliance(args.branch)

if __name__ == "__main__":
    main()
