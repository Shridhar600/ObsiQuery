from typing import List, Optional,Annotated
from src.graph.agent_state import AgentState
from src.utils import setup_logger
from src.llm import llm_instance
from src.models import VectorSearchOutputSchema
from src.prompts import get_rag_agent_prompt_template
from src.vector_store import similarity_search
from langchain_core.messages import  BaseMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool

log= setup_logger(__name__)

llm_with_structured_output = llm_instance.with_structured_output(schema=VectorSearchOutputSchema)

@tool(name_or_callable= 'rag_agent_tool',description=" This tool enables rag on user notes." )
def retrieve_notes_tool(query: str, state: Annotated[AgentState, InjectedState],):
    """
    Retrieves relevant information from user's notes.
    1. Uses an LLM to refine the query and derive metadata filters.
    2. Performs a vector search with these parameters.
    3. Synthesizes an answer from the results.
    Returns a dictionary with 'summary', 'retrieved_chunks_details'.
    """

    log.info(state)
    log.info(f"ReAct Agent has requested the Rag_agent_tool with query: {query}")
    
    # query_filters: VectorSearchOutputSchema = get_vector_search_filters_from_llm(query, state["messages"])
    # log.info(query_filters)
    # response = similarity_search(query_filter=query_filters)
    response = None
    if not response:
        log.warning("No chunks retrieved from vector store.")
        return {
            "summary": "I couldn't find any specific information in your notes related to that query.Maybe, we should retry with a more context full query",
            "retrieved_chunks_details": []
        }


def get_vector_search_filters_from_llm(query,message_history: Optional[List[BaseMessage]] = None) -> VectorSearchOutputSchema :
    """
    Uses an LLM to derive structured search parameters (refined query, metadata filters)
    from a natural language query and available filenames.
    """

    # available_file_names = get_file_names_from_cache()
    available_file_names_list = ["ObsiQuery - PRD.md", "sample_prd_project_alpha.md", "tech_notes_kafka.md", "meeting_notes_2023_10.md"] # Hardcoded for now
    
    # Format filenames for the prompt
    formatted_file_names = "\n".join([f"- {name}" for name in available_file_names_list])

    prompt_template = get_rag_agent_prompt_template()
    
    formatted_history = "No recent conversation history provided."
    if message_history:
        formatted_history = format_recent_history(message_history, last_n=5) # Get last 3


    prompt_variables = {
        "file_names": formatted_file_names,
        "input_query_from_react_agent": query,
        "conversation_history": message_history
    }

    prompt = prompt_template.invoke(prompt_variables)

    # log.info(f"final prompt: {prompt}")

    response: VectorSearchOutputSchema = llm_with_structured_output.invoke(prompt) # type: ignore
    return response


def format_recent_history(messages: List[BaseMessage], last_n: int = 5) -> str:
    """Formats the last N messages into a string for the prompt."""
    if not messages:
        return "No recent conversation history."
    
    recent_messages = messages[ -last_n :]
    formatted_lines = []
    for msg in recent_messages:
        role = "User" if msg.type == "human" else "Assistant" if msg.type == "ai" else msg.type
        formatted_lines.append(f"{role}: {msg.content}")
    return "\n".join(formatted_lines)
