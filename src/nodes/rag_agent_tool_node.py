from typing import Optional,Annotated
from src.graph.agent_state import AgentState
from src.utils import *
from src.llm import llm_instance
from src.models import VectorSearchOutputSchema
from src.prompts import get_rag_agent_prompt_template,get_synthesizer_agent_prompt_template
from src.vector_store import similarity_search
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool
from langchain_core.documents import Document

log= setup_logger(__name__)

llm_with_structured_output = llm_instance.with_structured_output(schema=VectorSearchOutputSchema)

@tool(name_or_callable= 'rag_agent_tool',response_format="content_and_artifact" )
def retrieve_notes_tool(query: str, state: Annotated[AgentState, InjectedState]) -> tuple:
    """
    Retrieves relevant information from user's notes.
    1. Uses an LLM to refine the query and derive metadata filters.
    2. Performs a vector search with these parameters.
    3. Synthesizes an answer from the results.
    Returns a dictionary with 'summary', 'retrieved_chunks_details'.
    """ 
    # log.info(state)
    log.info(f" -- ReAct Agent has requested the Rag_agent_tool with query: {query} -- ")

    formatted_history = get_formatted_convo_history(state)
    # log.info(f"formatted_history: ---  {formatted_history} " )
    # log.info("----------------------------------------------------------------------------------------------------------------------------------------------")
    
    query_filters: VectorSearchOutputSchema = get_vector_search_filters_from_llm(query,formatted_history )

    log.info(f" --  Output From the Vector Search Filter LLM : {query_filters} -- ")

    retrieved_context: Optional[list[Document]] = similarity_search(query_filter=query_filters)

    # retrieved_context = None

    if not retrieved_context:
        log.warning("No chunks retrieved from vector store.")
        return (
            "summary: I couldn't find any specific information in your notes related to that query.Maybe, we should retry with a more different query",
            [])
        
    
    else:
        log.info(" -- Synthesis LLM invoked by Rag_agent_tool --")

        context_string = "\n\n---\n\n".join([doc.page_content for doc in retrieved_context])

        synthesizer_prompt_template = get_synthesizer_agent_prompt_template()

        prompt_variables = {
        "Main_conversation_agent_Query": query,
        "conversation_history":formatted_history,
        "user_notes": context_string
        }

        synthesizer_prompt = synthesizer_prompt_template.invoke(prompt_variables)

        response = llm_instance.invoke(synthesizer_prompt)

        log.debug( f" --- Response Received from synthesizer Agent : {response.content} ")

        return response, query_filters.filenames_filter

def get_vector_search_filters_from_llm(query,formatted_history:str) -> VectorSearchOutputSchema :
    """
    Uses an LLM to derive structured search parameters (refined query, metadata filters)
    from a natural language query and available filenames.
    """

    log.info(" -- Vector Search Filter agent invoked by Rag_agent_tool --")

    # log.info(f"------------- query : {query}, message_history: {message_history} ")

    # available_file_names = get_file_names_from_cache()
    available_file_names_list = ["ObsiQuery - PRD.md", "sample_prd_project_alpha.md", "tech_notes_kafka.md", "meeting_notes_2023_10.md"] # Hardcoded for now
    
    # Format filenames for the prompt
    formatted_file_names = "\n".join([f"- {name}" for name in available_file_names_list])

    prompt_template = get_rag_agent_prompt_template()
    
    prompt_variables = {
        "file_names": formatted_file_names,
        "input_query_from_react_agent": query,
        "conversation_history": formatted_history
    }

    prompt = prompt_template.invoke(prompt_variables)

    # log.info(f"final prompt --------------------------- : {prompt}")

    response: VectorSearchOutputSchema = llm_with_structured_output.invoke(prompt) # type: ignore
    return response

