from langgraph.graph import StateGraph, START, END

from state import MentorState
from nodes import (
    risk_node,
    risk_router,
    scholarship_node,
    resource_node,
    intervention_node,
    low_risk_node
)

builder = StateGraph(MentorState)

# Nodes
builder.add_node("risk", risk_node)
builder.add_node("low_risk", low_risk_node)
builder.add_node("scholarship", scholarship_node)
builder.add_node("resource", resource_node)
builder.add_node("intervention", intervention_node)

# Start
builder.add_edge(START, "risk")

# Conditional routing
builder.add_conditional_edges(
    "risk",
    risk_router,
    {
        "low_risk": "low_risk",
        "scholarship": "scholarship"
    }
)

# Remaining workflow
builder.add_edge("scholarship", "resource")
builder.add_edge("resource", "intervention")
builder.add_edge("intervention", END)
builder.add_edge("low_risk", END)

graph = builder.compile()