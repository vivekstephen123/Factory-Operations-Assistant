"""
RAG Engine for Factory Operations Assistant.
Loads documents from documents/ directory, chunks them,
embeds them into ChromaDB, and provides search_documents() functionality.
"""

import os
import glob
import pymupdf
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "documents"))
CHROMA_PERSIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))

_collection = None


def extract_text_from_pdf(filepath: str) -> str:
    doc = pymupdf.open(filepath)
    text_content = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_content.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(text_content)


def init_rag_store(force_reindex: bool = False):
    global _collection
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    collection_name = "operations_manuals"
    
    if force_reindex:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    try:
        _collection = client.get_collection(name=collection_name, embedding_function=emb_fn)
        if _collection.count() > 0 and not force_reindex:
            return _collection
    except Exception:
        _collection = client.create_collection(name=collection_name, embedding_function=emb_fn)

    pdf_files = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
    if not pdf_files:
        try:
            from documents.generate_docs import generate_all
            generate_all()
            pdf_files = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
        except Exception as e:
            print(f"Could not auto-generate PDF documents: {e}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=75,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    docs_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    chunk_id = 0
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        raw_text = extract_text_from_pdf(pdf_path)
        chunks = text_splitter.split_text(raw_text)

        for idx, chunk in enumerate(chunks):
            chunk_id += 1
            docs_to_add.append(chunk)
            metadatas_to_add.append({
                "source": filename,
                "chunk_index": idx,
                "file_path": pdf_path
            })
            ids_to_add.append(f"doc_{chunk_id}_{filename}")

    if docs_to_add:
        _collection.add(
            documents=docs_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"Indexed {len(docs_to_add)} chunks from {len(pdf_files)} PDF files.")

    return _collection


def search_documents(query: str, top_k: int = 3) -> str:
    global _collection
    if _collection is None:
        _collection = init_rag_store(force_reindex=False)

    results = _collection.query(
        query_texts=[query],
        n_results=top_k
    )

    if not results or not results["documents"] or len(results["documents"][0]) == 0:
        return f"No relevant documentation found for query: '{query}'."

    output_lines = [f"Found {len(results['documents'][0])} relevant document passage(s):"]
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        source = meta.get("source", "Unknown Document")
        output_lines.append(f"\n--- [Source: {source}] ---")
        output_lines.append(doc.strip())

    return "\n".join(output_lines)
