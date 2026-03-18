# graph/graph_entry.py
"""
LangGraph Studio entry point.

Studio requires a module-level variable holding the compiled graph.
`langgraph.json` points to this file:  ./research_agent/graph/graph_entry.py:graph

Do NOT put any heavy logic here — just build and expose the graph.
The pipeline is run by invoking the graph with an initial state, which
Studio constructs from the GraphState schema automatically.
"""

from research_agent.graph.builder import build_graph

# Module-level compiled graph — Studio discovers this via the :graph suffix
# in langgraph.json
graph = build_graph()
