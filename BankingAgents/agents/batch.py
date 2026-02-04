from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END
import operator

from tools.mocks import MockTools

class BatchState(TypedDict):
    messages: Annotated[list, operator.add]
    job_id: str
    error_type: str
    retry_count: int

def check_job_status(state: BatchState):
    """Check the job status in DB."""
    job_id = state["job_id"]
    # Simulate DB query
    result = MockTools.db_query(f"SELECT * FROM batch_log WHERE job_id='{job_id}'")
    error = result[0].get("error", "Unknown")
    return {
        "messages": [f"Job Status: FAILED. Error: {error}"],
        "error_type": error
    }

def analyze_failure(state: BatchState):
    """Decide if failure is transient or data-related."""
    error = state["error_type"]
    if "Connection timed out" in error:
        return {"messages": ["Analysis: Transient Network Error identified."]}
    elif "DataIntegrityViolation" in error:
        return {"messages": ["Analysis: Data Quality Error identified."]}
    else:
        return {"messages": ["Analysis: Unknown error type."]}

def execute_retry(state: BatchState):
    """Retry the job."""
    return {
        "messages": ["Action: Retrying job... Success."],
        "retry_count": state["retry_count"] + 1
    }

def escalate(state: BatchState):
    """Escalate to human."""
    return {"messages": ["Action: Paging On-Call Support for Data Issue."]}

def route_action(state: BatchState):
    """Route based on analysis."""
    last_msg = state["messages"][-1]
    if "Transient" in last_msg:
        return "execute_retry"
    else:
        return "escalate"

# Build Graph
builder = StateGraph(BatchState)
builder.add_node("check_status", check_job_status)
builder.add_node("analyze", analyze_failure)
builder.add_node("execute_retry", execute_retry)
builder.add_node("escalate", escalate)

builder.add_edge(START, "check_status")
builder.add_edge("check_status", "analyze")
builder.add_conditional_edges("analyze", route_action, {
    "execute_retry": "execute_retry",
    "escalate": "escalate"
})
builder.add_edge("execute_retry", END)
builder.add_edge("escalate", END)

batch_agent = builder.compile()
