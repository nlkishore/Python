from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
import operator

from config import get_llm
from tools.mocks import MockTools

class SupportState(TypedDict):
    messages: Annotated[list, operator.add]
    server_host: str
    issue_detected: str
    logs: str
    action_plan: str

# Nodes
def diagnose_sys_health(state: SupportState):
    """Check system health via SSH."""
    host = state["server_host"]
    output = MockTools.ssh_execute("top -b -n 1 | head -n 5", host)
    return {
        "messages": [f"System Health Check on {host}: {output}"],
        "logs": output
    }

def analyze_logs(state: SupportState):
    """Check logs for known errors."""
    host = state["server_host"]
    # We simulate checking for OOM specifically if the scenario implies it
    # In a real agent, the LLM would decide what to grep based on the ticket
    output = MockTools.ssh_execute("grep -r 'OutOfMemory' /var/log/jboss", host)
    
    if "OutOfMemoryError" in output:
        issue = "Critical: OutOfMemory"
        plan = "Restart JBoss"
    else:
        issue = "Unknown"
        plan = "Investigate further"
        
    return {
        "messages": [f"Log Analysis: {output}"],
        "issue_detected": issue,
        "action_plan": plan
    }

def human_approval(state: SupportState):
    """Pause for human approval if action is risky."""
    issue = state["issue_detected"]
    plan = state["action_plan"]
    
    if issue == "Critical: OutOfMemory":
        # Interrupt the graph logic
        response = interrupt(f"Detected {issue}. Plan is to {plan}. Approve? (yes/no)")
        
        # Resume with response
        if response.lower() == "yes":
             return {"messages": ["Human approved restart."]}
        else:
             return {"messages": ["Human rejected restart."]}
    
    return {"messages": ["No approval needed for this state."]}

def execute_fix(state: SupportState):
    """Execute the fix if approved."""
    last_msg = state["messages"][-1]
    if "approved" in last_msg:
        output = MockTools.ssh_execute("service jboss restart", state["server_host"])
        return {"messages": [f"Fix Executed: {output}"]}
    else:
        return {"messages": ["Fix aborted by user."]}

def decide_next_step(state: SupportState):
    """Conditional logic."""
    if "approved" in state["messages"][-1]:
        return "execute_fix"
    elif "rejected" in state["messages"][-1]:
        return END
    
    # If we just corrected analyzed and found OOM, go to approval
    if state["issue_detected"] == "Critical: OutOfMemory":
        return "human_approval"
        
    return END

# Build Graph
builder = StateGraph(SupportState)
builder.add_node("diagnose", diagnose_sys_health)
builder.add_node("analyze", analyze_logs)
builder.add_node("human_approval", human_approval)
builder.add_node("execute_fix", execute_fix)

builder.add_edge(START, "diagnose")
builder.add_edge("diagnose", "analyze")
builder.add_conditional_edges("analyze", decide_next_step, {
    "human_approval": "human_approval",
    END: END
})
builder.add_conditional_edges("human_approval", decide_next_step, {
    "execute_fix": "execute_fix",
    END: END
})
builder.add_edge("execute_fix", END)

support_agent = builder.compile()
