# src/main.py
from dotenv import load_dotenv
load_dotenv()

import os
import yaml
import argparse
from pathlib import Path

from src.crew import run_pipeline
from src.tools.pdf_tools import load_pdf_text  # uses your existing PDF util

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    parser.add_argument("--top-k", type=int, default=6, help="RAG retrieval results per sub-query")
    parser.add_argument("--quiet", action="store_true", help="Suppress agent logs")
    args = parser.parse_args()

    # src/ as root for configs and cache
    root = Path(__file__).resolve().parent

    # Load agent/task configs
    agents = load_yaml(root / "agents.yaml")
    tasks  = load_yaml(root / "tasks.yaml")

    # Build/update a TXT cache for RAG tools (consumed by pdf_rag_search)
    txt_cache = root / "data" / "input" / "current.txt"   # -> src/data/input/current.txt
    txt_cache.parent.mkdir(parents=True, exist_ok=True)
    txt_cache.write_text(load_pdf_text(args.pdf), encoding="utf-8", errors="ignore")

    # Expose to tools
    os.environ["PDF_TXT_CACHE"] = str(txt_cache)

    # Run your Crew pipeline (printing handled inside run_pipeline)
    _ = run_pipeline(
        args.pdf,
        agents,
        tasks,
        top_k=args.top_k,
        verbose=not args.quiet
    )

