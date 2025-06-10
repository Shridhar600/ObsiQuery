from .agent_state import AgentState
from langgraph.graph import StateGraph, START
from src.nodes import react_agent_node
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from ..utils import setup_logger

log = setup_logger(__name__)

def create_simple_graph(llm_with_tools: BaseChatModel, memory, tools: list ) -> CompiledStateGraph:

    tools_node = ToolNode(tools)

    workflow = StateGraph(AgentState)
    workflow.add_node("reAct_agent_node", lambda state: react_agent_node(state, llm_with_tools))
    workflow.add_node("tools", tools_node)
    workflow.add_edge(START, "reAct_agent_node")
    workflow.add_conditional_edges(
        "reAct_agent_node", tools_condition
    )  # The tools_condition function exposes two edges for the Simple_chatbot Node 1. tools 2. END.
    workflow.add_edge("tools", "reAct_agent_node")
    graph = workflow.compile(checkpointer=memory, debug=False)
    log.info("Simple Graph compiled successfully.")
    return graph
