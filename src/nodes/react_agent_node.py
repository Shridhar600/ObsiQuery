from src.utils import setup_logger, get_system_time_info
from src.prompts import get_react_agent_prompt_template
from langchain_core.language_models.chat_models import BaseChatModel


log = setup_logger(__name__)


def react_agent_node(state:dict, llm_with_tools:BaseChatModel):
    """
    This function is a placeholder for the React Agent Node.
    It is currently not implemented and serves as a stub.
    """

    messages = state.get("messages")
    if not messages:
        log.warning("No messages found in the state at ChatAgentNode.")
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "No messages to process in graph's state at ChatAgentNode.",
                }
            ]
        }

    system_time_info = get_system_time_info()
    prompt_variables = state | system_time_info

    prompt_template  = get_react_agent_prompt_template()
    prompt = prompt_template.invoke(prompt_variables)

    response = llm_with_tools.invoke(prompt)
    # log.debug(f" ---  Response from REACT AGENT {response}")
    return {"messages" : [response]}