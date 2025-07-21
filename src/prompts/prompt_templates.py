from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .system_prompts import VECTOR_SEARCH_FILTER_AGENT_PROMPT,REACT_AGENT_SYSTEM_PROMPT,SYNTHESIS_AGENT_SYSTEM_PROMPT


def get_react_agent_prompt_template() -> ChatPromptTemplate:
    """
    Returns a ChatPromptTemplate for the main ReAct Agent.
    This agent acts as an experienced, collaborative technical partner.
    """
    system_prompt = REACT_AGENT_SYSTEM_PROMPT
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

def get_rag_agent_prompt_template() -> ChatPromptTemplate:

    system_prompt = VECTOR_SEARCH_FILTER_AGENT_PROMPT
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt) # this has files, conversation history for context and task briefing
            # ("assistant", "task_briefing_from_core_agent: {task_briefing_from_core_agent}") 
        ]
    )


def get_synthesizer_agent_prompt_template() -> ChatPromptTemplate:
    system_prompt = SYNTHESIS_AGENT_SYSTEM_PROMPT
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt)
        ]
    )