import os, pathlib

# --- Create folders ---
dirs = [
    "src",
    "src/tools",
    "src/data/input",
    "src/data/vectorstore",
    "src/data/output",
]
for d in dirs:
    pathlib.Path(d).mkdir(parents=True, exist_ok=True)

def write(path, content):
    pathlib.Path(path).write_text(content.strip() + "\n", encoding="utf-8")

# --- Top-level files ---
write("requirements.txt", """
crewai>=0.60
crewai-tools>=0.4
langchain>=0.2
langchain-community>=0.2
pydantic>=2
chromadb>=0.5
pypdf>=5
python-slugify>=8
tiktoken
openai>=1.35
PyYAML>=6
""")

write(".env.example", "OPENAI_API_KEY=sk-yourkey\nOPENAI_MODEL=gpt-4o-mini\n")

write(".gitignore", """
.venv/
__pycache__/
*.pyc
.env
src/data/vectorstore/
.DS_Store
""")

write("README.md", "# CrewAI BioLit → Blog\n\nRun `python src/main.py --pdf src/data/input/your.pdf` to generate a blog post.")

write("Dockerfile", """
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
COPY src/agents.yaml src/tasks.yaml ./src/
ENV PYTHONPATH=/app/src
CMD ["python", "src/main.py", "--pdf", "src/data/input/sample.pdf"]
""")

# --- Python package structure ---
write("src/__init__.py", "")
write("src/tools/__init__.py", "")

# --- Tools ---
write("src/tools/pdf_tools.py", """
from pypdf import PdfReader

def load_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for i, p in enumerate(reader.pages, start=1):
        txt = p.extract_text() or ""
        pages.append(f"[p.{i}]\\n{txt}")
    return "\\n\\n".join(pages)
""")

write("src/tools/rag_tools.py", """
import chromadb
from chromadb.config import Settings
from typing import List
import hashlib, os

def _doc_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def build_store(text: str, collection_name="biolit", persist_dir="src/data/vectorstore"):
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(allow_reset=True))
    col = client.get_or_create_collection(collection_name)
    chunks, size = [], 1200
    for i in range(0, len(text), size):
        chunk = text[i:i+size]
        chunks.append(chunk)
    if chunks:
        ids = [_doc_id(c) for c in chunks]
        col.upsert(ids=ids, documents=chunks, metadatas=[{}]*len(chunks))
    return col

def retrieve(query: str, k=5, collection_name="biolit", persist_dir="src/data/vectorstore") -> List[str]:
    client = chromadb.PersistentClient(path=persist_dir)
    col = client.get_or_create_collection(collection_name)
    res = col.query(query_texts=[query], n_results=k)
    return res.get("documents", [[]])[0] if res else []
""")

write("src/tools/seo_tools.py", """
from slugify import slugify

def make_slug(title: str) -> str:
    return slugify(title or "untitled")

def front_matter(meta: dict) -> str:
    tags = meta.get("tags", [])
    if isinstance(tags, (list, tuple)):
        tags_line = ", ".join(tags)
    else:
        tags_line = str(tags)
    title = (meta.get("title") or "").replace('"', '\\"')
    descr = (meta.get("meta_description") or "").replace('"', '\\"')
    slug = meta.get("slug", "")
    return (
        "---\\n"
        f'title: "{title}"\\n'
        f'description: "{descr}"\\n'
        f"slug: {slug}\\n"
        f"tags: [{tags_line}]\\n"
        "---\\n\\n"
    )
""")

# --- Agents + Tasks ---
write("src/agents.yaml", """
researcher:
  role: "Literature Researcher"
  goal: "Extract key claims, methods, and results with page references."
  backstory: "You are a rigorous scientific reader who ties notes to page numbers."
  verbose: true
  allow_delegation: false

writer:
  role: "Science Writer"
  goal: "Write a clear, engaging blog post (900–1200 words) for a smart non-expert."
  backstory: "You translate jargon into crisp prose and keep citations like [p.X]."
  verbose: true
  allow_delegation: false

seo_editor:
  role: "SEO Editor"
  goal: "Optimize title, slug, description, headings, excerpt, and tags."
  backstory: "Tasteful SEO; target 'what/why/how' intent without clickbait."
  verbose: true
  allow_delegation: false
""")

write("src/tasks.yaml", """
notes_task:
  description: |
    Read the PDF context and produce structured notes:
    - TL;DR (3 bullets)
    - Key claims (with page refs)
    - Methods (short)
    - Results (short, with metrics where possible)
    - Limitations (short)
  expected_output: "YAML or JSON block with TLDR, Claims, Methods, Results, Limitations."

draft_task:
  description: |
    Using the notes, write a blog post:
    - 900–1200 words
    - Intro that frames the question/problem
    - Clear sections with H2/H3
    - Inline citations like [p.12]
    - A short ‘Why it matters’ section
    - ‘Further reading’ list (3 items)
  expected_output: "Markdown article only."

seo_task:
  description: |
    Create SEO metadata:
    - title (<=60 chars), slug, meta_description (<=155 chars)
    - 5–7 tags
    - Improve headings (H2/H3) if needed
  expected_output: "JSON with {title, slug, meta_description, tags, updated_headings?}."
""")

# --- Crew wiring ---
write("src/crew.py", """
import os, json
from crewai import Agent, Task
from openai import OpenAI
from pathlib import Path
from .tools.pdf_tools import load_pdf_text
from .tools.rag_tools import build_store, retrieve
from .tools.seo_tools import make_slug, front_matter

def llm(prompt: str) -> str:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role":"user","content":prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content

def tool_retrieve(q: str) -> str:
    docs = retrieve(q, k=5)
    joined = "\\n---\\n".join(docs)
    return f"Retrieved context:\\n{joined}"

def make_agents(config: dict):
    researcher = Agent(**config["researcher"], llm=llm, tools=[tool_retrieve])
    writer = Agent(**config["writer"], llm=llm)
    seo = Agent(**config["seo_editor"], llm=llm)
    return researcher, writer, seo

def run_pipeline(pdf_path: str, agents_cfg: dict, tasks_cfg: dict, output_dir: str = "src/data/output"):
    text = load_pdf_text(pdf_path)
    build_store(text)
    researcher, writer, seo = make_agents(agents_cfg)
    notes = Task(**tasks_cfg["notes_task"], agent=researcher, context=[text]).execute()
    draft_md = Task(description=f"NOTES:\\n{notes}\\n\\nWrite the article.",
                    expected_output=tasks_cfg["draft_task"]["expected_output"], agent=writer).execute()
    meta_json = Task(description=f"ARTICLE HEADINGS + EXCERPT NEEDED. Return JSON.\\n{draft_md}\\n\\n",
                     expected_output=tasks_cfg["seo_task"]["expected_output"], agent=seo).execute()
    try:
        meta = json.loads(meta_json)
    except Exception:
        meta = {"title":"Untitled","slug":"untitled","meta_description":"", "tags":["science"]}
    meta["slug"] = meta.get("slug") or make_slug(meta.get("title","untitled"))
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir, f"{meta['slug']}.md").write_text(front_matter(meta) + draft_md, encoding="utf-8")
    return str(Path(output_dir, f"{meta['slug']}.md"))
""")

# --- Main ---
write("src/main.py", """
import os, yaml, argparse
from pathlib import Path
from crew import run_pipeline

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    agents = load_yaml(root / "agents.yaml")
    tasks  = load_yaml(root / "tasks.yaml")
    out = run_pipeline(args.pdf, agents, tasks)
    print(f"✅ Wrote: {out}")
""")

# --- Sample placeholder ---
write("src/data/input/sample.pdf", "Place a real PDF here before running.")

print("✅ Project scaffold created!")
print("Next:  python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt")
print("       cp .env.example .env  # add your OpenAI key")
print("       python src/main.py --pdf src/data/input/your.pdf")

