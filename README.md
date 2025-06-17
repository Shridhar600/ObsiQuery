# ObsiQuery

## Introduction

ObsiQuery is a local, privacy-preserving AI assistant that transforms your Obsidian markdown notes into a searchable and synthesizable "second brain." It enables you to interact with your notes using natural language questions and receive grounded, summarized answers with source references, all within a private, local environment.

## Key Features

*   **Natural Language Querying:** Ask questions about your notes using natural language.
*   **Grounded Responses:** Receive answers that are grounded in your notes, with source references.
*   **Local and Private:** All processing is done locally, ensuring your data privacy.
*   **Semantic Search:** Utilizes semantic search to find relevant information in your notes.
*   **Knowledge Synthesis:** Synthesizes information from multiple notes to provide comprehensive answers.
*   **Markdown-Aware Chunking:** Preserves markdown structure when chunking notes for vector storage.
*   **Change Tracking:** Efficiently manages the ingestion process by only re-processing files that are new, modified, or previously failed.

## Architecture Overview
![Recording 2025-06-16 192558](https://github.com/user-attachments/assets/2cedf3df-c5b4-453e-9d06-7c18015ffadf)

ObsiQuery consists of two principal layers:

1.  **Data Pipeline Layer:** Responsible for processing your local Obsidian markdown notes, extracting structure and content, splitting them into semantically meaningful chunks, enriching them with metadata, and storing their vector representations in a local database (ChromaDB).
2.  **Agentic Layer:** Powered by a primary ReAct agent. This layer handles user interaction, understands queries, and retrieves information from the processed notes via a specialized RAG tool.

### Data Pipeline Layer

The Data Pipeline Layer is responsible for the end-to-end process of ingesting user notes. It runs periodically to keep the knowledge base up-to-date. The pipeline is composed of six principal stages:

1.  **Source File Discovery & Metadata Collection:** Identifying markdown files in the user's vault and reading their basic filesystem metadata.
2.  **File Logging & Change Tracking (`obq_log`):** Maintaining a persistent record of files, detecting modifications or previous failures, and marking files for processing using a SQLite database log (`obq_log`).
3.  **Processing Orchestration & Selection:** Querying the log table to select files that are ready to be processed in the current pipeline run based on their status and enabled state.
4.  **File Loading & Markdown-Aware Chunking:** Loading the content of selected files and splitting it into semantically meaningful chunks while preserving markdown structure.
5.  **Vector Store Management & Chunk Logging (`obq_chunk_log`):** Handling the interaction with the local vector database (ChromaDB) to upload new chunks and delete outdated ones for modified files, tracking chunk IDs in a separate log table (`obq_chunk_log`).
6.  **Vector Search Interface:** Providing a defined function (`similarity_search`) that the Agentic Layer uses to query the processed data in the vector store.

### Agentic Layer

The Agentic Layer serves as the user-facing intelligence and control center for ObsiQuery. Its architecture is centered around a conversational AI agent capable of understanding natural language requests and leveraging specialized tools to fulfill them. The key components and their interactions are:

*   **User Interface:** The frontend where users input queries and receive responses.
*   **Main ReAct Agent:** The primary conversational agent responsible for receiving user input, analyzing intent, maintaining conversation state, deciding on actions (including tool use), and formulating final responses.
*   **`retrieve_notes_tool`:** A crucial, specialized tool available to the Main ReAct Agent. It encapsulates the entire complex RAG (Retrieval-Augmented Generation) workflow needed to query the user's knowledge base.
*   **Internal RAG Agents/Components:** Within the `retrieve_notes_tool`, dedicated LLM instances or logical units (Retriever/Filter Agent, Synthesizer Agent) handle specific RAG sub-tasks like determining search parameters and generating summaries.

## Setup Instructions

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure environment variables:**
    *   Copy the contents of `.env.example` to a new file named `.env`.
    *   Modify the variables in the `.env` file to match your environment.
    *   Set the `OBSIDIAN_VAULT_PATH` variable to the path of your Obsidian vault.
    *   Configure other environment variables as needed.
3.  **Run the Streamlit UI:**
    ```bash
    streamlit run streamlit_ui.py
    ```
    Note: The data pipeline can be run from the Streamlit UI.

## Usage Instructions

1.  Open the Streamlit UI in your browser.
2.  Enter your query in the text box.
3.  Click the "Send" button.
4.  The AI assistant will respond with an answer based on your notes.

## Contribution Guidelines

Contributions are welcome! Please follow these guidelines:

*   Fork the repository.
*   Create a new branch for your feature or bug fix.
*   Write tests for your code.
*   Submit a pull request.
