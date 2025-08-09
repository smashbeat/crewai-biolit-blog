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
