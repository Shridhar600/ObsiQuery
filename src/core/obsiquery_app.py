from src.utils import setup_logger
from src.llm import llm_instance
from src.nodes import retrieve_notes_tool
from langgraph.checkpoint.memory import InMemorySaver
from src.graph import create_simple_graph
from langchain_core.messages import HumanMessage

log = setup_logger(__name__)

class ObsiQueryBot:
    def __init__(self):
        self.memory = self._initialize_memory_saver()
        self.tools = self._initialize_tools()
        self.llm = self._initialize_llm_with_tools()
        self.graph = self._initialize_graph()
        log.info("ObsiQueryBot initialized")

    def _initialize_llm(self):
        log.info("LLM instance initialized for ObsiQueryBot")
        return llm_instance

    def _initialize_memory_saver(self):
        log.info("Memory initialized for ObsiQueryBot")
        return InMemorySaver()

    def _initialize_tools(self) -> list:
        # might have to make a tools registry. TODO
        log.info("Tools initialized for ObsiQueryBot")
        return [retrieve_notes_tool]

    def _initialize_llm_with_tools(self):
        log.info("LLM instance with Tools initialized for ObsiQueryBot")
        return llm_instance.bind_tools(self.tools)

    def _initialize_graph(self):
        log.info("Graph initialized for ObsiQueryBot")
        return create_simple_graph(llm_with_tools=self.llm,memory=self.memory,tools=self.tools)
    
    def get_thread_config(self, thread_id: str) -> dict:
        """Generates the LangGraph configuration for a given thread_id."""
        return {"configurable": {"thread_id": thread_id}}    
    
    def invoke_graph(self, user_input: str , thread_id: str):
        """Invokes the LangGraph with user input for a specific thread."""

        if not user_input or not thread_id:
            log.error("User input and thread_id are required for graph invocation.")
            return {"error": "Missing user input or thread ID."}  
              
        config = self.get_thread_config(thread_id)
        log.debug(f"Invoking graph for thread '{thread_id}' with input: '{user_input}'")

        try:
            response = self.graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config) # type: ignore
            log.debug(f"Graph response for thread '{thread_id}': {response}")

            if response and "messages" in response and response["messages"]:
                return {"reply": response["messages"][-1].content, "full_response": response} # Return more if needed by UI
            return {"reply": "No message found in graph's response.", "full_response": response}
        except Exception as e:
            log.exception(f"Error invoking graph for thread '{thread_id}': {e}")
            return {"error": str(e), "full_response": None}
