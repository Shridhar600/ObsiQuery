from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document


markdown_path = "C:/Users/SHRIDHAR/Desktop/pro/Obsidian-RAG/README.md"
loader = UnstructuredMarkdownLoader(markdown_path, mode="paged")

data = loader.load()
print(f"Number of documents: {len(data)}\n")

for document in data:
    print(f"{document}\n")