import chromadb
from chromadb.config import Settings

_client_cache = {}

def _get_client(persist_dir: str):
    key = persist_dir
    if key not in _client_cache:
        _client_cache[key] = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(allow_reset=True)
        )
    return _client_cache[key]

from typing import List
import hashlib, os

def _doc_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def build_store(text: str, collection_name="biolit", persist_dir="src/data/vectorstore"):
    os.makedirs(persist_dir, exist_ok=True)
    client = _get_client(persist_dir)
    col = client.get_or_create_collection(collection_name)
    chunks, size = [], 1200
    for i in range(0, len(text), size):
        chunk = text[i:i+size]
        chunks.append(chunk)
    if chunks:
        ids = [_doc_id(c) for c in chunks]
        col.upsert(ids=ids, documents=chunks, metadatas=[{"source":"pdf","chunk": i} for i in range(len(chunks))])
    return col

def retrieve(query: str, k=5, collection_name="biolit", persist_dir="src/data/vectorstore") -> List[str]:
    client = _get_client(persist_dir)
    col = client.get_or_create_collection(collection_name)
    res = col.query(query_texts=[query], n_results=k)
    return res.get("documents", [[]])[0] if res else []
# --- CrewAI tool wrapper ------------------------------------------------------
import os, json
from crewai.tools import tool

@tool("pdf_rag_search")
def pdf_rag_search(query: str) -> str:
    """
    Query the Chroma vector store built from the current PDF text cache.
    Returns JSON: {"snippets":[{text, source, chunk, distance}]}
    """
    persist_dir = os.getenv("VECTORSTORE_DIR", "src/data/vectorstore")
    collection_name = os.getenv("VECTORSTORE_COLLECTION", "biolit")
    try:
        k = int(os.getenv("RAG_TOP_K", "5"))
    except ValueError:
        k = 5

    # Lazily build the store from the TXT cache if empty
    client = _get_client(persist_dir)
    col = client.get_or_create_collection(collection_name)
    need_build = False
    try:
        need_build = (col.count() == 0)
    except Exception:
        need_build = True

    if need_build:
        txt_path = os.getenv("PDF_TXT_CACHE", "src/data/input/current.txt")
        if os.path.exists(txt_path):
            text = open(txt_path, "r", encoding="utf-8", errors="ignore").read()
            build_store(text, collection_name=collection_name, persist_dir=persist_dir)
            col = client.get_or_create_collection(collection_name)

    res = col.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )
    docs  = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    snippets = []
    for i, text in enumerate(docs):
        md = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
        dist = dists[i] if i < len(dists) else None
        snippets.append({
            "text": text,
            "source": md.get("source", "pdf"),
            "chunk": md.get("chunk"),
            "distance": dist
        })
    return json.dumps({"snippets": snippets}, ensure_ascii=False)

