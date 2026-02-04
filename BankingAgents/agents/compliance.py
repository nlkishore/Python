from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END
import operator

from tools.mocks import MockTools

class ComplianceState(TypedDict):
    messages: Annotated[list, operator.add]
    branch_name: str
    diff_content: str
    violations: list

def fetch_diff(state: ComplianceState):
    """Get the code changes."""
    branch = state["branch_name"]
    diff = MockTools.bitbucket_diff(branch)
    return {
        "messages": [f"Fetched diff for {branch}"],
        "diff_content": diff
    }

def scan_code(state: ComplianceState):
    """Scan for forbidden patterns."""
    diff = state["diff_content"]
    violations = []
    
    if "System.out.println" in diff:
        violations.append("Forbidden: Use Logger instead of System.out.println")
        
    if "password" in diff and "Debug" in diff:
        violations.append("Security Risk: Potential hardcoded password in debug")
        
    return {
        "messages": [f"Scan Complete. Found {len(violations)} violations."],
        "violations": violations
    }

def generate_report(state: ComplianceState):
    """Generate final report."""
    violations = state["violations"]
    if not violations:
        return {"messages": ["Compliance Check PASSED."]}
    
    report = "\n".join([f"- {v}" for v in violations])
    return {"messages": [f"Compliance Check FAILED:\n{report}"]}

# Build Graph
builder = StateGraph(ComplianceState)
builder.add_node("fetch_diff", fetch_diff)
builder.add_node("scan", scan_code)
builder.add_node("report", generate_report)

builder.add_edge(START, "fetch_diff")
builder.add_edge("fetch_diff", "scan")
builder.add_edge("scan", "report")
builder.add_edge("report", END)

compliance_agent = builder.compile()
