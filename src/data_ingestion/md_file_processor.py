from typing import Any, Dict, List
from src.utils import setup_logger,config
from src.models import FileMetadata
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from src.models import FileMetadata
from markdown_it import MarkdownIt


log = setup_logger(__name__)

SemanticBlock = Dict[str, Any]  

def load_markdown_file(file: FileMetadata) -> List[Document]:
    """
    Loads a Markdown file into LangChain Documents, enriched with metadata.
    Returns an empty list if the file is invalid or has no loadable content.
    """
    metadata = {"source": file.file_path, "log_id": file.id}
    documents: List[Document] = []
    try:
        # loaded = UnstructuredMarkdownLoader(file.file_path).load()
        loaded = TextLoader(file.file_path,encoding='utf-8').load()  # Using TextLoader to preserve headers
        for doc in loaded:
            documents.append(Document(page_content=doc.page_content, metadata=metadata))
        # log.info(f"Loaded {len(documents)} documents from file: {file.file_path}")
        if not documents:
            log.warning(f"Empty document list after loading: {file.file_path}")
    except FileNotFoundError:
        log.error(f"File not found during load: {file.file_path}", exc_info=True)
    except Exception as e:
        log.error(f"Unhandled exception while loading file: {file.file_path}. Error: {e}", exc_info=True)

    return documents

def chunk_documents(documents: List[Document], file_metadata: FileMetadata ) -> List[Document]:
    """
    Orchestrates the Markdown chunking process:
    1. Consume raw text from the TextLoader Document.
    2. Get semantic blocks using markdown-it-py.
    3. Assemble blocks into LangChain Document chunks with overlap and metadata.
    Assumes input 'documents' is a list containing a single Document from TextLoader. idk why but langchain load method emits a list of Documents containing a single Document.
    Returns a list of Document chunks.
    """
    if not documents or not documents[0].page_content:
         log.warning(f"No content found for chunking in {file_metadata.file_path}") 
         return []

    raw_text = documents[0].page_content # Get raw text from TextLoader Document

    semantic_blocks = get_semantic_blocks(raw_text)
    log.info(f"Extracted {len(semantic_blocks)} semantic blocks from {file_metadata.file_path}")

    if not semantic_blocks:
        log.warning(f"No semantic blocks extracted from {file_metadata.file_path}") 
        return []

    # Step 2: Assemble chunks from blocks
    final_chunks = assemble_chunks_from_semantic_blocks(
        semantic_blocks,
        config.CHUNK_SIZE, # type: ignore
        config.CHUNK_OVERLAP, # type: ignore
        file_metadata.file_path, # Pass source
        file_metadata.id,    # Pass log_id
        file_metadata.file_name
    )
    # for chunk in final_chunks:
    #     log.info(f'Final Chunk:{chunk}')
    #     log.info('_______________________________________---------------------________________________________________')

    return final_chunks

def assemble_chunks_from_semantic_blocks(
    semantic_blocks: List[SemanticBlock],
    chunk_size: int,
    overlap: int,
    source: str,
    log_id: int,
    file_name: str
) -> List[Document]:
    """
    Assembles a list of semantic blocks (including headings) into LangChain Document chunks
    respecting chunk_size, overlap, and metadata.
    """
    final_chunks: List[Document] = []
    current_chunk_strings: List[str] = [] # Stores raw content strings for the current chunk
    current_chunk_blocks: List[SemanticBlock] = [] # Stores block objects for metadata lookup (first block's header)

    # Store blocks from the *previous* finalized chunk to generate overlap for the *next* chunk.
    # store the actual blocks because we need their content and header 
    previous_chunk_blocks: List[SemanticBlock] = []

    # Helper to calculate current buffer length including separators
    def get_current_buffer_len(parts: List[str]) -> int:
        """Calculates length of joined string with '\n\n' separators."""
        return len("\n\n".join(parts)) if parts else 0

    # Helper to create a chunk Document
    def create_chunk_document(content_parts: List[str], blocks_in_chunk: List[SemanticBlock]):
         """Creates a LangChain Document from content parts and block metadata."""
         page_content = "\n\n".join(content_parts).strip() # Strip final chunk content

         section_title = blocks_in_chunk[0]['header'] if blocks_in_chunk else ""

         return Document(
             page_content=page_content,
             metadata={'source': source, 'file_name': file_name, 'log_id': log_id, 'section_title': section_title}
         )

    for i, block in enumerate(semantic_blocks):
        block_text = block['content']
        block_type = block['type']
        block_header = block['header'] # Header associated with this specific block

        # Assumes a "\n\n" separator if the buffer is not empty
        potential_buffer_strings = current_chunk_strings + [block_text]
        potential_len = get_current_buffer_len(potential_buffer_strings)

        # Case 1: Current block is individually larger than chunk_size.
        # Process as a standalone chunk if it's the first block we consider for a chunk.
        is_oversized_block = not current_chunk_strings and len(block_text) > chunk_size

        if is_oversized_block:
             log.debug(f"Creating oversized chunk for block type: {block_type}")
             # Create a chunk just for this block. Its header is its own associated header.
             final_chunks.append(
                 Document(
                     page_content=block_text.strip(), # Strip content of the single block chunk
                     metadata={'source': source, 'file_name': file_name, 'log_id': log_id, 'section_title': block_header}
                 )
             )
             # previous_chunk_blocks remains unchanged from before this oversized block.
             continue # Move to the next block


        # Case 2: Adding current block makes the current chunk buffer exceed chunk_size
        elif potential_len > chunk_size:
            log.debug(f"Chunk size exceeded ({potential_len} > {chunk_size}) by block type: {block_type}. Finalizing current chunk.")
            # Finalize the current chunk (excluding the block that would exceed)
            final_chunks.append(create_chunk_document(current_chunk_strings, current_chunk_blocks))

            # Save blocks from this just-finalized chunk for potential overlap in the *next* chunk
            previous_chunk_blocks = current_chunk_blocks[:] # Shallow copy

            current_chunk_strings = []
            current_chunk_blocks = []

            overlap_parts: List[str] = [] # Stores the string content parts for the overlap

            header_to_add = block_header.strip() # Use the header associated with the CURRENT block
            if header_to_add:

                 temp_overlap_blocks: List[SemanticBlock] = []
                 temp_overlap_len = 0
                 overlap_separator_len = len("\n\n") # Assume separators between overlap parts
                 for j in range(len(previous_chunk_blocks) - 1, -1, -1):
                      prev_b = previous_chunk_blocks[j]
                      prev_block_text = prev_b['content']

                      # Calculate potential length if we add this block's content + separator if not the first overlap part
                      len_to_add = len(prev_block_text) + (overlap_separator_len if temp_overlap_len > 0 else 0)

                      if temp_overlap_len + len_to_add <= overlap:
                          temp_overlap_blocks.insert(0, prev_b) # Insert at the start to maintain order (oldest first)
                          temp_overlap_len += len_to_add
                      else:
                           break # Adding this block would exceed total overlap limit, stop.

                 # The content for the overlap part is the joined content of temp_overlap_blocks
                 # These are already in correct order 
                 overlap_parts = [b['content'] for b in temp_overlap_blocks]

                 # If overlap was generated add it to the new chunk buffer
                 if overlap_parts:
                      current_chunk_strings.extend(overlap_parts)
                      # current_chunk_blocks DON'T include overlap blocks for the purpose of section_title 

            current_chunk_strings.append(block_text)
            current_chunk_blocks.append(block) 

        else: # current_chunk_strings is empty aur adding fits
            current_chunk_strings.append(block_text)
            current_chunk_blocks.append(block)

    if current_chunk_strings:
        log.debug(f"Finalizing last chunk with {len(current_chunk_strings)} parts.")
        final_chunks.append(create_chunk_document(current_chunk_strings, current_chunk_blocks))

    # log.info(f"Assembled {len(final_chunks)} chunks.")
    return final_chunks


def get_semantic_blocks(raw_markdown_text: str) -> List[SemanticBlock]:
    """
    Parses markdown text using markdown-it-py and extracts semantic blocks
    (headings, paragraphs, code, lists, etc.) with associated headers.
    Uses token.map for precise text extraction from original lines.
    Headers are included as distinct 'heading' blocks.
    """
    md = MarkdownIt()
    tokens = md.parse(raw_markdown_text)
    lines = raw_markdown_text.split('\n')

    semantic_blocks: List[SemanticBlock] = []
    current_header_text: str = ""
    i = 0 # Token index

    while i < len(tokens):
        token = tokens[i]
        token_type = token.type


        if token_type == 'heading_open':
            # The text of the heading is in the next token, which is inline
            # Get stripped header text first to set current_header_text immediately
            header_text_stripped = ""
            next_token = tokens[i + 1]
            if next_token.type == 'inline' and next_token.content:
                 header_text_stripped = next_token.content.strip()
            current_header_text = header_text_stripped # Update tracker

            # Now extract the raw markdown header line(s) using token.map
            header_content = ""
            if token.map: # Ensure map exists for this token
                start_line, end_line_exclusive = token.map
                header_lines = lines[start_line : end_line_exclusive]
                header_content = "\n".join(header_lines)

            # Add the heading as a semantic block itself
            if header_content.strip(): # Add block only if it has content 
                 semantic_blocks.append({
                     'type': 'heading', # Explicitly label this block as a heading
                     'content': header_content, # Raw markdown header text 
                     'header': header_text_stripped # Store stripped text as well
                 })

            i += 3
            continue 

        # Identify block-level tokens that we want to treat as semantic units
        is_semantic_block_start = token_type in [
            'paragraph_open',      # Standard paragraph
            'fence',               # Fenced code block (```)
            'code_block',          # Indented code block
            'blockquote_open',     # Blockquote (> ...)
            'bullet_list_open',
            'ordered_list_open',
            'list_item_open',      # Individual list item
            'html_block',          # Raw HTML block
            'hr',                  # Horizontal rule (---)
        ]

        if is_semantic_block_start and token.map:
             # token.map is usually [start_line_0_indexed, end_line_0_indexed + 1]
             start_line, end_line_exclusive = token.map

             # Slice the original lines to get the block's text
             block_content_lines = lines[start_line : end_line_exclusive]
             block_content = "\n".join(block_content_lines)


             block_type = token_type.replace('_open', '')
             if token_type in ['fence', 'code_block']: block_type = 'code_block'
             if token_type in ['bullet_list_open', 'ordered_list_open']: block_type = 'list' 
             if token_type == 'list_item_open': block_type = 'list_item' # Keep list item specific

             if block_content.strip():
                  semantic_blocks.append({
                     'type': block_type,
                     'content': block_content,
                     'header': current_header_text 
                  })

             if token_type in ['fence', 'code_block', 'hr', 'html_block']:
                  i += 1
                  continue

             if token_type in ['paragraph_open', 'blockquote_open', 'list_item_open']:
                  close_tag_type = token_type.replace('_open', '_close')
                  k = i + 1
                  nesting_level = 1 
                  while k < len(tokens):
                       if tokens[k].type == token_type: 
                            nesting_level += 1
                       elif tokens[k].type == close_tag_type:
                            nesting_level -= 1
                            if nesting_level == 0:
                                 i = k + 1 
                                 break 
                       k += 1

                  if k == len(tokens):
                       i += 1 
                  continue 

             if token_type in ['bullet_list_open', 'ordered_list_open']:
                 close_tag_type = token_type.replace('_open', '_close')
                 k = i + 1
                 nesting_level = 1
                 while k < len(tokens):
                     if tokens[k].type == token_type:
                         nesting_level += 1
                     elif tokens[k].type == close_tag_type:
                         nesting_level -= 1
                         if nesting_level == 0:
                              i = k + 1
                              break
                     k += 1
                 if k == len(tokens): i += 1
                 continue

             log.warning(f"Unhandled semantic block type for index advancement: {token_type} at token index {i}")
             i += 1 # Fallback advancement
             continue

        i += 1

    log.debug(f"Extracted {len(semantic_blocks)} semantic blocks.")

    return semantic_blocks