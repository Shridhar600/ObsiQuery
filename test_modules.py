import threading
import asyncio
import time
import warnings
import atexit
import tracemalloc
import logging

from src.core.data_pipeline import run_ingestion_test
from src.nodes.react_agent_node import react_agent_node
from src.nodes.rag_agent_tool_node import get_vector_search_filters_from_llm, retrieve_notes_tool

# =============================
# Setup: Debugging Hooks
# =============================

# warnings.simplefilter("default")  # Show ResourceWarnings
# tracemalloc.start()               # Track memory allocations

# Optional: Log where your program exits
# @atexit.register
# def on_exit():
#     print("\n👋 Program is trying to exit.")
#     print("🔎 Checking for leftover threads...\n")
#     time.sleep(0.5)
#     for t in threading.enumerate():
#         print(f"🧵 Thread: {t.name}, Daemon: {t.daemon}")

#     try:
#         loop = asyncio.get_event_loop()
#         if loop.is_running():
#             tasks = asyncio.all_tasks(loop)
#             print(f"🌀 {len(tasks)} async task(s) still running:")
#             for task in tasks:
#                 print(f" - {task}")
#     except RuntimeError:
#         # No event loop
#         pass

#     print("✅ Exit hooks complete.")


# =============================
# Main Run
# =============================

if __name__ == "__main__":
   #  logging.basicConfig(level=logging.DEBUG)
   #  logging.debug("🚀 Starting ingestion test")
    
   # run_ingestion_test()
   # response = react_agent_node({
   #      "messages": [
   #          {"role": "user", "content": "Hello, how are you?"}
   #      ]
   #  })

   retrieve_notes_tool("file name is obsiquery and vector search could be done using obsiquery prd.")
    
   #  logging.debug("🛑 Ingestion test finished")

