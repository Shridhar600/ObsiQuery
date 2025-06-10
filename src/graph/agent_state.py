from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict): 
    """
    Represents the state of the graph, containing the history of messages.
    """
    messages: Annotated[list, add_messages]
