from typing import List, Dict, Any
from crewai_tools import tool
import json, yaml, os

# Minimal RAG over a prebuilt vectorstore (or simple text load if you prefer)
@tool("pdf_rag_search")
def pdf_rag_search(query: str) -> str:
    """
    Search the loaded PDF chunks for relevant passages.
    Returns a JSON string with 'snippets': [{text, source, page}].
    """
    # If you already have a vectorstore in src/data/vectorstore, load it.
    # Otherwise, fall back to a naive text scan over a cached txt dump.
    # Keep it simple for now.
    txt_path = os.getenv("PDF_TXT_CACHE", "src/data/input/current.txt")
    results = []
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # naive scan
        hits = []
        for line in text.splitlines():
            if len(line) > 80 and any(q.lower() in line.lower() for q in query.split()):
                hits.append({"text": line.strip(), "source": "pdf", "page": None})
            if len(hits) >= 8:
                break
        results = hits
    return json.dumps({"snippets": results})

@tool("json_validate")
def json_validate(json_text: str) -> str:
    """
    Validates the provided text as JSON, returns 'ok' or an error message.
    """
    try:
        json.loads(json_text)
        return "ok"
    except Exception as e:
        return f"error: {e}"

@tool("yaml_validate")
def yaml_validate(yaml_text: str) -> str:
    """
    Validates the provided text as YAML, returns 'ok' or an error message.
    """
    try:
        yaml.safe_load(yaml_text)
        return "ok"
    except Exception as e:
        return f"error: {e}"

