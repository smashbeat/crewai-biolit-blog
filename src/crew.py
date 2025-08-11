# src/crew.py
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from crewai import Agent, Task, Crew, Process

from src.tools.pdf_tools import load_pdf_text
from src.tools.rag_tools import build_store, pdf_rag_search  # uses your Chroma + tool wrapper

__all__ = ["run_pipeline"]  # make import explicit: from src.crew import run_pipeline

# ---------------- helpers ----------------
def _safe_slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def _ext_for_task_id(tid: str) -> str:
    t = (tid or "").lower()
    if "plan" in t or "yaml" in t or "outline" in t: return ".yaml"
    if "json" in t or "facts" in t or "fact" in t:   return ".json"
    return ".md"

def _extract_text(payload: Any) -> str:
    for attr in ("raw", "output", "result", "final_output", "content", "text"):
        if hasattr(payload, attr):
            v = getattr(payload, attr)
            if isinstance(v, str) and v.strip():
                return v
    if isinstance(payload, (dict, list)):
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception:
            return str(payload)
    return str(payload)

def _ensure_vectorstore(pdf_path: str, top_k: int) -> Tuple[str, str]:
    """Build/refresh a Chroma collection for this PDF. Uses PDF_TXT_CACHE if set."""
    persist_dir = os.environ.setdefault("VECTORSTORE_DIR", "src/data/vectorstore")
    slug = _safe_slug(Path(pdf_path).stem)
    collection_name = os.environ.setdefault("VECTORSTORE_COLLECTION", slug)
    os.environ.setdefault("RAG_TOP_K", str(top_k))

    txt_path = os.getenv("PDF_TXT_CACHE")
    if txt_path and Path(txt_path).exists():
        text = Path(txt_path).read_text(encoding="utf-8", errors="ignore")
    else:
        text = load_pdf_text(pdf_path)

    build_store(text, collection_name=collection_name, persist_dir=persist_dir)
    return collection_name, persist_dir

# ---------------- tool registry ----------------
_TOOL_REGISTRY = {
    "pdf_rag_search": pdf_rag_search,
}

# ---------------- builders ----------------
def _build_agent(name: str, spec: Dict[str, Any]) -> Agent:
    role       = spec.get("role", name)
    goal       = spec.get("goal", "")
    backstory  = spec.get("backstory", "")
    model      = spec.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    verbose    = bool(spec.get("verbose", False))
    tool_names = spec.get("tools", []) or []
    tools = [_TOOL_REGISTRY[t] for t in tool_names if t in _TOOL_REGISTRY]

    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        model=model,
        verbose=verbose,
        tools=tools or None,
        allow_delegation=False,
    )

def _build_task(spec: Dict[str, Any], agent: Agent) -> Task:
    return Task(
        description=spec.get("description", ""),
        expected_output=spec.get("expected_output", ""),
        agent=agent,
    )

# ---------------- public entry ----------------
def run_pipeline(
    pdf_path: str,
    agents_cfg: Dict[str, Any],
    tasks_cfg: Any,
    output_dir: str = "src/data/output",
    top_k: int = 6,
    verbose: bool = True,
) -> Dict[str, str]:
    """Run Crew from YAML configs and save artifacts. Returns {task_id: filepath}."""
    _ensure_vectorstore(pdf_path, top_k)

    # Build agents
    agents: Dict[str, Agent] = {name: _build_agent(name, spec) for name, spec in (agents_cfg or {}).items()}

    # Normalize tasks format
    if isinstance(tasks_cfg, list):
        task_specs = tasks_cfg
    elif isinstance(tasks_cfg, dict) and "tasks" in tasks_cfg:
        task_specs = tasks_cfg["tasks"]
    else:
        raise ValueError("tasks.yaml must be a list, or a dict with key 'tasks'.")

    tasks: List[Task] = []
    task_ids: List[str] = []
    for i, ts in enumerate(task_specs):
        agent_name = ts.get("agent")
        if not agent_name or agent_name not in agents:
            raise ValueError(f"Task {i} references unknown agent '{agent_name}'.")
        tasks.append(_build_task(ts, agents[agent_name]))
        task_ids.append(ts.get("id") or ts.get("name") or f"task{i+1}")

    crew = Crew(agents=list(agents.values()), tasks=tasks, process=Process.sequential, verbose=verbose)
    result = crew.kickoff()

    # Collect outputs in order
    outputs: List[Any] = []
    if isinstance(result, (list, tuple)):
        outputs = list(result)
    else:
        for t in tasks:
            out = getattr(t, "output", None) or getattr(t, "result", None)
            outputs.append(out if out is not None else result)

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(Path(pdf_path).stem)

    saved: Dict[str, str] = {}
    for i, payload in enumerate(outputs):
        text = _extract_text(payload)
        tid  = task_ids[i] if i < len(task_ids) else f"task{i+1}"
        ext  = _ext_for_task_id(tid)
        path = outdir / f"{slug}-{tid}{ext}"
        path.write_text(text, encoding="utf-8")
        saved[tid] = str(path)

    if verbose:
        print("✅ CrewAI pipeline complete. Artifacts:")
        for k, v in saved.items():
            print(f" - {k}: {v}")

    return saved

