from typing import List, Optional
from src.utils import setup_logger,config
from src.models import FileMetadata
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document
from src.models import FileMetadata

log = setup_logger(__name__)

def load_markdown_file(file: FileMetadata) -> List[Document]:
    """
    Loads a Markdown file into LangChain Documents, enriched with metadata.
    Returns an empty list if the file is invalid or has no loadable content.
    """
    metadata = {"source": file.file_path, "log_id": file.id}
    documents: List[Document] = []

    try:
        loaded = UnstructuredMarkdownLoader(file.file_path).load()
        for doc in loaded:
            documents.append(Document(page_content=doc.page_content, metadata=metadata))
        log.info(f"Loaded {len(documents)} documents from file: {file.file_path}")
        if not documents:
            log.warning(f"Empty document list after loading: {file.file_path}")

    except FileNotFoundError:
        log.error(f"File not found during load: {file.file_path}", exc_info=True)
    except Exception as e:
        log.error(f"Unhandled exception while loading file: {file.file_path}. Error: {e}", exc_info=True)

    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Chunk documents intelligently with section-awareness and overlap.
    """
    chunked_docs = []
    for doc in documents:
        try:
            blocks = split_into_markdown_blocks(doc.page_content)
            if not blocks:
                log.warning(f"No valid blocks found in document: {doc.metadata.get('source')}")
                continue
            chunks = assemble_chunks_from_blocks(
                blocks, 
                chunk_size=config.CHUNK_SIZE,
                overlap=config.CHUNK_OVERLAP,
                base_metadata=doc.metadata
            )
            chunked_docs.extend(chunks)
        except Exception as e:
            log.error(f"Error chunking document {doc.metadata.get('source')}: {e}", exc_info=True)

    return chunked_docs


def split_into_markdown_blocks(content: str) -> List[str]:
    """
    Split markdown content into logical blocks.
    Preserves entire code blocks enclosed by triple backticks.
    Other content is split using empty lines as separators.
    """
    blocks = []
    buffer = []
    in_code_block = False
    code_fence = None  # Track ``` or ~~~ for code blocks
    code_block_counter = 0

    try:
        lines = content.splitlines()

        for line in lines:
            stripped = line.strip()

            # Detect code block start/end
            if stripped.startswith("```") or stripped.startswith("~~~"):## here we can also make it like if there's a code block then block should have the previous line as well so that we can preserve the code block title as well.
                if in_code_block:
                    # Closing a code block
                    buffer.append(line)
                    block = "\n".join(buffer).strip()
                    blocks.append(block)
                    buffer = []
                    in_code_block = False
                    code_fence = None
                    code_block_counter += 1
                else:
                    # Starting a new code block
                    if buffer:
                        block = "\n".join(buffer).strip()
                        blocks.append(block)
                        buffer = []
                    buffer.append(line)
                    in_code_block = True
                    code_fence = stripped[:3]  # Store ``` or ~~~
            elif in_code_block:
                buffer.append(line)
            elif stripped == "":
                # Paragraph break
                if buffer:
                    block = "\n".join(buffer).strip()
                    blocks.append(block)
                    buffer = []
            else:
                buffer.append(line)

        # Handle leftover buffer
        if buffer:
            block = "\n".join(buffer).strip()
            blocks.append(block)

        # Check for unclosed code block
        if in_code_block:
            log.warning("Unclosed code block detected. Flushing anyway.")
        
        final_blocks = [block for block in blocks if block]

        # #just for debugging
        # for blocksd in final_blocks:
        #     log.info(f"block produced = {blocksd}")

        log.info(f"Total code blocks detected: {code_block_counter}")
        log.info(f"Total blocks produced: {len(final_blocks)}")
        return final_blocks

    except Exception as e:
        log.exception("Error while splitting markdown blocks.")
        return []

def assemble_chunks_from_blocks(
    blocks: List[str],
    chunk_size: int,
    overlap: int,
    base_metadata: Optional[dict] = None
) -> List[Document]:
    """
    Create overlapping chunks from markdown blocks, preserving section titles in metadata.
    """
    chunks = []
    current_chunk = []
    current_length = 0
    current_section_title = "Unknown"

    # First, tag each block with the current section heading
    block_section_pairs = []
    for block in blocks:
        # header_match = re.match(r"^\s*(#{1,6})\s+(.*)", block) # this is not working because of UnstructuredMarkdownLoader stripping the headers, might need to use a simple text loader to preserve headers
        # if header_match:
        #     current_section_title = header_match.group(2).strip()
        block_section_pairs.append((block, current_section_title))

    i = 0
    while i < len(block_section_pairs):
        block, section = block_section_pairs[i]
        block_length = len(block)
        # here we check if the current block can fit into the current chunk if yes, then we add it to the current chunk
        if current_length + block_length <= chunk_size: # Check if adding this block exceeds the chunk size.
            current_chunk.append((block, section)) # Add block and section to current chunk
            current_length += block_length # Update current length
            i += 1
        else:
            # finalize the current chunk
            chunk_text = "\n\n".join([b for b, _ in current_chunk])
            metadata = dict(base_metadata or {})
            # metadata["section_title"] = most_common_section_title(current_chunk)
            metadata["section_title"] = "Unknown"
            chunks.append(Document(page_content=chunk_text, metadata=metadata))

            # Overlap window
            overlap_chunk = []
            overlap_len = 0
            for b, s in reversed(current_chunk):
                if overlap_len + len(b) <= overlap:
                    overlap_chunk.insert(0, (b, s)) # Add to the front block of the overlap chunk
                    overlap_len += len(b)
                else:
                    break

            current_chunk = overlap_chunk
            current_length = sum(len(b) for b, _ in current_chunk)

    # Final chunk
    if current_chunk:
        chunk_text = "\n\n".join([b for b, _ in current_chunk])
        metadata = dict(base_metadata or {})
        # metadata["section_title"] = most_common_section_title(current_chunk)
        metadata["section_title"] = "Unknown"
        chunks.append(Document(page_content=chunk_text, metadata=metadata))

    return chunks


# def most_common_section_title(chunks: List[tuple]) -> str: #doesn't work right now.
#     """
#     Get the most common section title in the chunk. Fallback to last if uncertain.
#     """
#     from collections import Counter
#     section_counts = Counter(section for _, section in chunks if section)
#     if section_counts:
#         return section_counts.most_common(1)[0][0]
#     return "Unknown"
