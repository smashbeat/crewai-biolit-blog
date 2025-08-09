from dotenv import load_dotenv
load_dotenv()
import os, yaml, argparse
from pathlib import Path
from src.crew import run_pipeline

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    parser.add_argument("--top-k", type=int, default=6, help="RAG retrieval results per sub-query (default: 6)")
    parser.add_argument("--quiet", action="store_true", help="Suppress agent logs")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    agents = load_yaml(root / "agents.yaml")
    tasks  = load_yaml(root / "tasks.yaml")
    out = run_pipeline(args.pdf, agents, tasks, top_k=args.top_k, verbose=not args.quiet)
    # print suppressed (see crew.py)
