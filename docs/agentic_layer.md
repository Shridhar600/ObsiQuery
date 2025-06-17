**1. Introduction**

*   **Problem:** Traditional knowledge management systems, like Obsidian vaults, primarily rely on manual browsing and keyword search. As the volume of notes grows, users struggle to efficiently find specific insights, recall nuanced information, or synthesize knowledge across their collection using natural language queries.
*   **Goal:** To build a fully local, privacy-preserving AI assistant that transforms a user's Obsidian markdown notes into a searchable and synthesizable "second brain." This enables users to interact with their notes using natural language questions and receive grounded, summarized answers with source references, all within a private, local environment.
*   **Project Summary:** ObsiQuery is a system designed to unlock the potential of personal knowledge bases. It consists of two principal layers:
    1.  A **robust data pipeline** responsible for processing the user's local Obsidian markdown notes, extracting structure and content, splitting them into semantically meaningful chunks, enriching them with metadata, and storing their vector representations in a local database.
    2.  An **intelligent agentic layer** powered by a primary ReAct agent. This layer handles user interaction, understands queries, and retrieves information from the processed notes via a specialized RAG tool. This RAG tool itself orchestrates complex internal logic, including filter generation based on the query and available note context, vector search, and synthesis of retrieved information using dedicated sub-agents. This layered agentic approach ensures relevant, grounded responses or facilitates planning and discussion, all while maintaining the user's data privacy by operating entirely locally.

**2. Overall Agentic Layer Architecture**

The Agentic Layer serves as the user-facing intelligence and control center for ObsiQuery. Its architecture is centered around a conversational AI agent capable of understanding natural language requests and leveraging specialized tools to fulfill them. The key components and their interactions are:

*   **User Interface:** The frontend where users input queries and receive responses. The Agentic Layer operates behind this interface.
*   **Main ReAct Agent:** The primary conversational agent responsible for receiving user input, analyzing intent, maintaining conversation state, deciding on actions (including tool use), and formulating final responses.
*   **`retrieve_notes_tool`:** A crucial, specialized tool available to the Main ReAct Agent. It encapsulates the entire complex RAG (Retrieval-Augmented Generation) workflow needed to query the user's knowledge base.
*   **Internal RAG Agents/Components:** Within the `retrieve_notes_tool`, dedicated LLM instances or logical units (Retriever/Filter Agent, Synthesizer Agent) handle specific RAG sub-tasks like determining search parameters and generating summaries.

The interaction flow typically begins with a user query received by the Main ReAct Agent.

**3. The Main ReAct Agent: Role and Processing Flow**

The Main ReAct Agent is the central intelligence coordinating user interactions and task execution in ObsiQuery. It operates using the ReAct (Reason-Act-Observe) paradigm, allowing it to perform iterative reasoning, decide on specific actions (like using a tool), execute that action, observe the result, and then incorporate that observation into subsequent reasoning steps.

*   **Core Responsibility:** To serve as the primary conversational partner, understand and interpret user queries within the context of the ongoing dialogue, determine the appropriate next step (respond directly, retrieve information, engage in planning, etc.), and formulate the final output presented to the user.
*   **Input:** Receives the raw natural language query from the user interface and has access to the complete history of the current conversation thread via the graph state.
*   **Initial Processing and Decision Making:**
    *   Upon receiving a new query or observation, the agent analyzes it using its internal reasoning capabilities, guided by its detailed system prompt which defines its persona and available capabilities.
    *   It evaluates the query and history to determine the user's intent and whether the required information or capability is readily available (e.g., general knowledge, information already discussed) or needs to be retrieved from the user's notes.
    *   **Action Decision:**
        *   If the query can be fully addressed based on its internal state or general knowledge, the agent formulates and outputs a direct natural language response to the user.
        *   If the agent determines that the query necessitates accessing specific information stored within the user's Obsidian notes, it decides to utilize its primary tool: the `retrieve_notes_tool`.
*   **Query Formulation for RAG Tool:** When the agent decides to invoke the `retrieve_notes_tool`, it doesn't simply pass the raw user query. Instead, it **reasons about the user's original request in the context of the full conversation history and formulates a specific, optimized query string**. This formulated query is designed to be a clear and effective prompt for the RAG process, aiming to maximize the chances of retrieving relevant information. This formulated query is passed as the primary argument to the `retrieve_notes_tool`.

**4. The `retrieve_notes_tool`: Specialized RAG Sub-Process**

The `retrieve_notes_tool` serves as the specialized interface to the user's knowledge base. When invoked by the Main ReAct Agent with a formulated query and the graph state, it orchestrates a sophisticated internal process involving dedicated components to perform Retrieval-Augmented Generation.

*   **Input Reception:** Receives the formulated query string (optimized for retrieval) from the Main ReAct Agent and extracts the last 5 messages from the conversation history available in the graph state for contextual awareness.
*   **Filter Generation (via Retriever Agent/LLM):**
    *   A dedicated internal LLM instance, acting as a "Retriever Agent" or "Filter Generation LLM," is the first step.
    *   This agent receives the formulated query from the Main ReAct Agent, the last 5 messages of conversation history, and is powered by a system prompt that provides crucial environmental context (its specific role within the RAG tool, its position in the overall agent graph, awareness of the other agents it collaborates with) and, importantly, access to a **list of all filenames successfully processed into the vector store.**
    *   Leveraging this comprehensive context, the Retriever Agent analyzes the query and history to infer the user's intent regarding specific documents or topics, utilizing the filename list to inform and refine its understanding.
    *   It generates a structured output containing:
        *   A **refined query string** specifically tailored for optimal semantic vector search.
        *   **Metadata filters**, including a list of target filenames. This list is translated into a metadata filter condition (using a "$in" style OR operator on the designated filename metadata field in the vector store), designed to constrain the subsequent vector search to only the most relevant files identified by the agent.
    *   *Purpose:* This step encapsulates the complex task of translating a natural language request into precise, structured parameters needed for an efficient and targeted vector database query, effectively offloading this specialized reasoning from the main agent.
*   **Vector Search Execution:**
    *   Using the refined query string (which is embedded) and the generated metadata filters from the Retriever Agent's output, the system performs a `similarity_search` query on the ChromaDB vector store.
    *   The search is efficiently restricted to chunks whose metadata matches the derived filters, ensuring results are both semantically relevant and contextually appropriate (e.g., from the specified file(s)).
*   **Synthesis (via Synthesizer Agent/LLM):**
    *   If the vector search successfully retrieves one or more relevant chunks (represented as LangChain `Document` objects), another dedicated internal LLM instance, acting as the "Synthesizer Agent" or "Synthesis LLM," is invoked.
    *   This agent receives the list of retrieved documents (chunks), the query passed to the `retrieve_notes_tool`, the last 5 messages of conversation history, and a system prompt defining its role: to generate a concise, fluent answer that directly addresses the user's query by synthesizing information *strictly* from the provided retrieved context. It is explicitly instructed not to invent information (prevent hallucination) and to format the output appropriately for consumption by the Main ReAct Agent. It is also aware of its environment and collaborators.
    *   *Purpose:* This agent performs the crucial "Generation" step of RAG, transforming raw, potentially disparate retrieved document segments into a cohesive, natural language answer that is grounded in the user's own notes.
*   **Output Formatting and Return:**
    *   The output from the Synthesizer Agent (the summary) is captured.
    *   The list of unique file names from the original retrieved `Document` objects is extracted to serve as source references.
    *   The `retrieve_notes_tool` returns a **LangChain Tool Message** back to the Main ReAct Agent. The synthesized summary is placed in the `content` field of the tool message. The list of unique source file names is included in the `artifact` field.

**5. Main ReAct Agent: Post-Retrieval Processing**

Upon receiving the `Tool Message` observation from the `retrieve_notes_tool`, the Main ReAct Agent integrates this new information into its ongoing reasoning process within the ReAct loop.

*   **Observe:** The agent incorporates the received `Tool Message` into its state. It primarily focuses on the synthesized `summary` contained in the `content` field. While the source file list in the `artifact` is available (and potentially used for display), the agent's subsequent decisions are driven by the summary content.
*   **Reason:** The agent analyzes the received `summary`. It critically assesses its relevance, completeness, and sufficiency by comparing the information presented in the summary against the original user's query and the current context and goals of the ongoing conversation. **The agent relies solely on the synthesized summary for this assessment; it does not process the raw retrieved chunks itself.**
*   **Act:** Based on its assessment of the summary, the agent decides the most appropriate next action within its ReAct loop:
    *   **Formulate Final User Response:** If the synthesized `summary` is deemed relevant and fully sufficient to answer the user's query, the agent crafts the final natural language response to the user. This response is based *primarily* on the content of the received summary.
    *   **Further Action:** If the summary is deemed insufficient, irrelevant, if the original query had multiple parts not yet addressed, or if the conversation needs to pivot (e.g., from retrieval to planning), the agent decides on an alternative action. This could involve invoking the `retrieve_notes_tool` again with a refined query (perhaps informed by the partial results or source files), transitioning to a different conversational mode (if other capabilities exist), or requesting clarification from the user to refine its understanding or the next step.

The Agentic Layer thus provides a flexible, multi-turn conversational experience. The Main ReAct Agent intelligently orchestrates interaction, leveraging the specialized RAG tool as a key capability to access and synthesize information from the user's notes, guided by its own reasoning and the flow of the conversation.