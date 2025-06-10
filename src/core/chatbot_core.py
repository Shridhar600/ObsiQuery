from regex import T
from src.graph import create_simple_graph
from src.llm import llm_instance
from src.nodes import rag_agent_tool_node
from langgraph.checkpoint.memory import InMemorySaver




tools: list = [rag_agent_tool_node]

llm_with_tools = llm_instance.bind_tools(tools)
memory = InMemorySaver()
graph = create_simple_graph(llm_with_tools=llm_with_tools,memory= memory, tools=tools) #type: ignore

def test_run():
    while True:
        user_input = input("User: ")
        response = graph.invoke(input = user_input)
        print(response)
