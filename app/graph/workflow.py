from langgraph.graph import StateGraph, END
from app.graph.state import HospitalState
from app.graph.nodes.intake import intake_node
from app.graph.nodes.priority import priority_node
from app.graph.nodes.resource import resource_node
from app.graph.nodes.optimizer import optimizer_node


def should_continue(state: dict) -> str:
     """Route based on errors."""
     if state.get("errors"):
          return "end"
     return "continue"


def build_graph():
     builder = StateGraph(HospitalState)

     #Nodes
     builder.add_node("intake", intake_node)
     builder.add_node("priority", priority_node)
     builder.add_node("resource", resource_node)
     builder.add_node("optimize", optimizer_node)

     #Entry 
     builder.set_entry_point("intake")

     #conditional routing after intake
     builder.add_conditional_edges(
          "intake",
          should_continue,
          {"continue":"priority", "end": END}
     )

     builder.add_edge("priority","resource")
     builder.add_edge("resource", "optimize")
     builder.add_edge("optimize", END)

     return builder.compile()


#singleton graph
_graph = None


def get_graph():
     global _graph
     if _graph is None:
          _graph = build_graph()
     return _graph

