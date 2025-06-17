**1. Introduction**

*   **Problem:** Users store valuable information in local markdown files, particularly within tools like Obsidian. However, accessing, searching, and synthesizing insights from these notes using natural language is challenging with traditional methods limited to simple keyword matching or manual navigation.
*   **Goal:** To build a robust and privacy-preserving data pipeline that transforms a user's collection of local Obsidian markdown notes into a structured, queryable knowledge base suitable for advanced AI retrieval and generation. The pipeline must handle file changes, ensure data integrity, and operate entirely locally.
*   **Project Summary:** ObsiQuery aims to be a local AI assistant for personal notes. Its foundation is the Data Pipeline Layer, which systematically processes the user's markdown vault. This layer handles discovering files, tracking their status and changes, parsing and chunking their content in a markdown-aware manner, embedding these chunks, and storing them in a local vector database. This prepared data then serves as the knowledge source for the Agentic Layer.

**2. Data Pipeline High-Level Stages**

The Data Pipeline Layer is responsible for the end-to-end process of ingesting user notes. It runs periodically via a cron job to keep the knowledge base up-to-date. The pipeline is composed of six principal stages that process files from discovery through to vector storage and search readiness:

1.  **Source File Discovery & Metadata Collection:** Identifying markdown files in the user's vault and reading their basic filesystem metadata.
2.  **File Logging & Change Tracking (`obq_log`):** Maintaining a persistent record of files, detecting modifications or previous failures, and marking files for processing using a SQLite database log (`obq_log`).
3.  **Processing Orchestration & Selection:** Querying the log table to select files that are ready to be processed in the current pipeline run based on their status and enabled state.
4.  **File Loading & Markdown-Aware Chunking:** Loading the content of selected files and splitting it into semantically meaningful chunks while preserving markdown structure, using a custom logic built with `markdown-it-py`.
5.  **Vector Store Management & Chunk Logging (`obq_chunk_log`):** Handling the interaction with the local vector database (ChromaDB) to upload new chunks and delete outdated ones for modified files, tracking chunk IDs in a separate log table (`obq_chunk_log`).
6.  **Vector Search Interface:** Providing a defined function (`similarity_search`) that the Agentic Layer uses to query the processed data in the vector store.

Each file selected for processing moves sequentially through stages 4 and 5. Stage 6 is a callable interface used by the Agentic Layer.

**3. Stage 1: Source File Discovery & Metadata Collection**

This initial stage initiates the data pipeline's processing cycle, typically triggered at regular intervals by a cron job. Its primary function is to locate all potential source markdown files within the user-specified Obsidian vault directory. The process involves a recursive scan of the entire directory tree. For each file identified as a markdown file (`.md` extension), the pipeline collects essential metadata directly from the filesystem:

*   **File Path (`file_path`):** The unique, absolute path to the file on the local filesystem.
*   **File Name (`file_name`):** The base name of the file.
*   **Last Modified Timestamp (`last_modified`):** The timestamp indicating the last time the file was modified. This is the primary mechanism for detecting changes in Stage 2.
*   **File Size (`file_size`):** The size of the file. *Note: Currently used for logging purposes only within the `obq_log` and not for change detection logic.*

File hashing is not currently part of the metadata collection process or used for detecting file changes.

**4. Stage 2: File Logging & Change Tracking (`obq_log`)**

This stage is fundamental to the pipeline's ability to efficiently manage the ingestion process and only re-process files that are new, modified, or previously failed. It utilizes the `obq_log` SQLite database table to maintain a persistent state of each markdown file discovered.

*   **`obq_log` Table Schema:**
    ```sql
    create table obq_log (
        id INTEGER primary key autoincrement,
        file_name TEXT not null,
        file_path TEXT not null unique,
        file_hash TEXT, -- Not currently used in logic
        file_size INTEGER, -- For logging only
        last_modified REAL not null, -- Last modified timestamp from filesystem
        last_ingested REAL, -- Timestamp of the last successful completion of Stages 4 & 5
        num_chunks INTEGER, -- Number of chunks generated in the last successful ingestion
        status TEXT not null check (status IN ('pending', 'processing', 'completed', 'failed')), -- Current processing status
        error_message TEXT, -- Details if processing failed
        metadata_json TEXT, -- For storing structured metadata parsed from file (e.g., frontmatter - Future Scope)
        created_at REAL default (STRFTIME('%s', 'now')), -- Timestamp of log entry creation
        is_enabled BOOLEAN default 1 -- Flag to control if the file should be processed
    );
    ```
*   **Comparison and Status Update Logic:** For each file found in Stage 1, its current filesystem metadata is compared against the entry in `obq_log` corresponding to its `file_path`.
    *   **New Files:** If a `file_path` found in Stage 1 does not exist in the `obq_log` table, a new row is inserted. The `status` is set to `'pending'`, the current `last_modified` timestamp is recorded, and `is_enabled` defaults to `1` (True).
    *   **Existing Files:** If a `file_path` already has an entry in `obq_log`:
        *   The current filesystem `last_modified` timestamp is compared with the `last_modified` timestamp stored in the log. If they are different, the file has been modified. The logged `status` is updated to `'pending'`, and the logged `last_modified` is updated to the current filesystem value.
        *   If the current `last_modified` is the same as the logged value, but the logged `status` is `'failed'`, the status is updated to `'pending'` to ensure the file is re-attempted in the next processing run.
        *   If the current `last_modified` is the same and the logged `status` is `'completed'`, the file is considered up-to-date and does not require processing in this run (unless `is_enabled` was manually changed, though the primary 'pending' trigger is modification or previous failure).
    *   Other fields like `file_size` and potentially `file_name` are updated to reflect the current filesystem state.

This stage ensures the `obq_log` table accurately reflects the presence and state of all markdown files and flags those requiring processing (`'pending'` or `'failed'`) for the next stage.

**5. Stage 3: Processing Orchestration & Selection**

This stage acts as the control point, determining precisely which files identified and tracked in Stage 2 will be processed in the current run of the pipeline. It queries the `obq_log` table to build the list of files to ingest.

The criteria for selecting a file for processing are:

*   The file's `status` must be either `'pending'` or `'failed'`. These statuses indicate that the file is new, modified since the last successful ingestion, or failed in a previous attempt and needs to be retried.
*   The file's `is_enabled` flag must be `TRUE`. This allows users to manually exclude specific files from ingestion.

The pipeline retrieves a list of files matching these criteria. For each file selected from this list, **immediately before** its content is passed to the document loading step (the beginning of Stage 4), the `status` for that specific file's entry in the `obq_log` table is updated to `'processing'`. This state change indicates that the file is currently being handled by the pipeline, which is useful for logging and preventing potential concurrent processing issues if the pipeline were scaled. The pipeline then proceeds to sequentially process each file in the selected list through the subsequent stages (4 and 5).

**6. Stage 4: File Loading & Markdown-Aware Chunking**

This is a core transformation stage where the raw content of a markdown file is broken down into structured chunks suitable for embedding and vector storage. This stage is executed for each file selected in Stage 3.

*   **File Loading:** The raw text content of the selected markdown file is loaded using a simple text loader, such as LangChain's `TextLoader`. A basic text loader is chosen specifically because it preserves the original markdown syntax (headers, code fences, list markers, etc.), which is crucial for the subsequent custom chunking logic. The output is typically a single LangChain `Document` object containing the file's full content and basic metadata like the file path.
*   **Markdown-Aware Chunking Logic:** The raw text content is then passed to a custom chunking process built using the `markdown-it-py` parser. This logic is designed to understand the structural elements of markdown:
    *   It uses `markdown-it-py` to parse the text into a stream of tokens, which describe the document's structure (headings, paragraphs, code blocks, list items, etc.).
    *   It iterates through these tokens, identifying "semantic blocks" – logical units of content like paragraphs, complete code blocks (`fence`/`code_block` tokens), list items (`list_item_open`/`list_item_close`), blockquotes, etc.
    *   Crucially, it leverages the `token.map` attribute provided by `markdown-it-py` to extract the *exact raw markdown text segment* corresponding to each identified semantic block from the original file content. This preserves the original formatting within each block.
    *   During this process, it also tracks the text of the most recently encountered heading (`#`, `##`, etc.) to associate content with its section. Heading lines themselves are also extracted as distinct 'heading' semantic blocks using `token.map` and included in the stream.
    *   These identified semantic blocks (each a unit of raw markdown text with its type and associated header) are then assembled into the final chunks that will be stored in the vector database.
    *   **Chunk Assembly:** The assembly process iterates through the semantic blocks, adding their content to a current chunk buffer. It respects a configured `chunk_size` (maximum desired characters per chunk) and `overlap` (number of characters to overlap between consecutive chunks).
    *   **Semantic Integrity:** A key aspect of this custom logic is preserving the integrity of atomic blocks like fenced code blocks. If a single semantic block is larger than the `chunk_size`, it is processed as a single oversized chunk (Option A) rather than being arbitrarily split, ensuring code syntax remains intact.
    *   **Intelligent Overlap:** Overlap is handled by including the raw markdown content of the section header and/or the last few semantic blocks from the end of the previous chunk at the start of the new chunk, prioritizing semantic units rather than arbitrary character counts where possible, while staying within the configured `overlap` size limit.
*   **Output:** The output of this stage is a list of enriched LangChain `Document` objects for the processed file. Each `Document` contains:
    *   `page_content`: The raw markdown text of the chunk, including any overlap.
    *   `metadata`: A dictionary including `source` (the file path), `log_id` (the ID from the `obq_log` entry for this file), and `section_title` (the text of the header associated with the beginning of this chunk). Future enhancements may include parsing and adding Obsidian frontmatter or other metadata here.

This stage is critical for ensuring that the data in the vector store is not only split but also structured in a way that retains the semantic relationships and formatting necessary for effective RAG.

**7. Stage 5: Vector Store Management & Chunk Logging (`obq_chunk_log`)**

This stage is responsible for interacting with the local ChromaDB vector store and maintaining a precise log of which chunks belong to which source file using the `obq_chunk_log` table. This is essential for managing updates and deletions. This stage is executed for each file after its chunks have been generated in Stage 4.

*   **`obq_chunk_log` Table Schema:**
    ```sql
    create table obq_chunk_log (
        id INTEGER primary key autoincrement,
        file_id INTEGER not null references obq_log, -- Foreign key linking to the source file
        chunk_id TEXT not null, -- The unique ID of the chunk in the vector store
        created_at REAL default (STRFTIME('%s', 'now'))
    );
    ```
*   **Deletion of Old Chunks:** Before uploading new chunks for a file, the pipeline checks if chunks for this `file_id` (from the `obq_log` entry) already exist in the vector store. It queries the `obq_chunk_log` table using the `file_id`. If matching entries are found, it means this file was previously processed and its chunks were uploaded. The system retrieves the `chunk_id`s from these `obq_chunk_log` entries. The corresponding entries in `obq_chunk_log` for this `file_id` are then deleted. Finally, the retrieved `chunk_id`s are used to delete the actual, outdated chunks from the ChromaDB vector store. This process ensures that modifications to a source file correctly result in the removal of its old chunks.
*   **Uploading New Chunks:** The list of new `Document` objects generated in Stage 4 is uploaded to the ChromaDB vector store. During this process, a unique UUID (Universally Unique Identifier) is generated for each `Document` object. These UUIDs serve as the persistent identifiers for the chunks within the vector store.
*   **Logging New Chunks:** After the successful upload of the new chunks to ChromaDB, their generated UUIDs (`chunk_id`s) are logged in the `obq_chunk_log` table. Each entry links the new `chunk_id` back to the `file_id` of the source file in the `obq_log` table. This maintains the necessary relationship between files and their constituent chunks for future updates or deletions.
*   **Updating File Status:** Upon successful completion of the deletion, upload, and chunk logging steps for a file, the `status` for that file's entry in the `obq_log` table is updated to `'completed'`. The `last_ingested` timestamp in `obq_log` is set to the current time. If any error occurred during loading, chunking, deletion, uploading, or logging, the status for that file is instead updated to `'failed'`, and relevant details are recorded in the `error_message` field of the `obq_log`.

This stage ensures that the vector store is synchronized with the latest version of the user's notes and that the database logs accurately reflect the state of both files and their associated chunks.

**8. Stage 6: Vector Search Interface**

This final stage represents the callable component of the Data Pipeline Layer that is directly utilized by the Agentic Layer (specifically, by the `retrieve_notes_tool`). Its purpose is to provide an efficient and filtered search capability over the processed and stored chunks.

*   **Input:** The `similarity_search` function receives a structured input, typically an object or dictionary corresponding to the `VectorSearchOutputSchema`. This input is generated by the Retriever Agent within the Agentic Layer's `retrieve_notes_tool` and contains the parameters needed for the search:
    *   `refined_query_for_vector_search`: The query string optimized for semantic vector search. This string is used to generate the query embedding.
    *   `metadata_filters`: A dictionary containing general key-value filters to apply to the search results (e.g., `{'project': 'ObsiQuery'}`).
    *   `filter_by_filenames`: An optional list of specific filenames.
*   **Process:**
    *   The function constructs the final filter dictionary required by the underlying ChromaDB vector store. It combines any general `metadata_filters` provided.
    *   Crucially, if a list of `filter_by_filenames` is provided, it translates this list into a ChromaDB filter condition using the `$in` operator (e.g., `{"source": {"$in": ["file1.md", "file2.md"]}}`), ensuring that the search is restricted to chunks originating from *any* of the files in the list. The key used (e.g., `"source"`) must match the metadata key stored during ingestion (Stage 4).
    *   It then executes the vector similarity search on the `vector_store_instance` (ChromaDB) using the query embedding derived from `refined_query_for_vector_search` and the constructed filter dictionary.
    *   The search is configured to return a specified number (`k`) of the most similar `Document` objects that match the filters.
    *   Basic error handling is included to catch exceptions during the search process.
*   **Output:** The function returns a list of relevant LangChain `Document` objects retrieved from the vector store. Each `Document` includes its `page_content` (the chunk's text) and `metadata` (containing the original `source` file path, `section_title`, `log_id`, etc.). If no relevant documents are found or an error occurs, an empty list is returned.

This stage provides the necessary data access layer, allowing the Agentic Layer to retrieve relevant, filtered, and structured chunks from the user's knowledge base based on semantic similarity and explicit metadata constraints derived from the user's query and available files.