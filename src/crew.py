import os, json
from pathlib import Path
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

from .tools.pdf_tools import load_pdf_text
from .tools.rag_tools import build_store, retrieve
from .tools.seo_tools import make_slug, front_matter

load_dotenv()

# ----------------------------
# LLM wrapper
# ----------------------------
def llm(messages_or_text, model=None, temperature=0.3):
    """Accepts either a string (user prompt) or a list of chat messages."""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if isinstance(messages_or_text, str):
        messages = [{"role": "user", "content": messages_or_text}]
    else:
        messages = messages_or_text
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

# ----------------------------
# Agents
# ----------------------------
def researcher_agent(pdf_text: str, top_k: int = 6) -> str:
    """Retrieval-grounded notes using Chroma vector store."""
    # Helper to pull context for a sub-question
    def _ctx(q: str, k: int = top_k) -> str:
        docs = retrieve(q, k=k)
        return "\n---\n".join(docs) if docs else ""

    # Focused sub-queries to get balanced coverage
    sections = {
        "Claims": _ctx("key claims, conclusions, headline findings"),
        "Methods": _ctx("methods, study design, sample, procedure, instrumentation"),
        "Results": _ctx("results, metrics, outcomes, effect sizes, statistics"),
        "Limitations": _ctx("limitations, caveats, biases, threats to validity"),
        "TLDRctx": _ctx("overall summary, safety implications, takeaways"),
    }

    prompt = (
        "You are a meticulous Research Analyst. Using ONLY the provided context blocks, "
        "produce structured notes:\n\n"
        "- TL;DR (3 bullets)\n"
        "- Key claims (with page refs like [p.12])\n"
        "- Methods (short)\n"
        "- Results (short, include metrics if present)\n"
        "- Limitations (short)\n\n"
        "Return YAML or JSON with keys: TLDR, Claims, Methods, Results, Limitations.\n\n"
        f"== CONTEXT: TLDR ==\n{sections['TLDRctx']}\n\n"
        f"== CONTEXT: CLAIMS ==\n{sections['Claims']}\n\n"
        f"== CONTEXT: METHODS ==\n{sections['Methods']}\n\n"
        f"== CONTEXT: RESULTS ==\n{sections['Results']}\n\n"
        f"== CONTEXT: LIMITATIONS ==\n{sections['Limitations']}\n"
    )
    return llm([
        {"role": "system", "content": "Be precise. Cite page refs like [p.N] from context only."},
        {"role": "user", "content": prompt},
    ], temperature=0.2)


def writer_agent(research_notes: str) -> str:
    """Turns researcher notes into a clear, engaging article."""
    prompt = (
        "You are an excellent Science Writer. Using the NOTES below, write a blog article (900–1200 words) for a smart non-expert:\n"
        "- Start with an intro framing the question/problem\n"
        "- Use H2/H3 sections\n"
        "- Keep inline citations like [p.12] from the notes\n"
        "- Include a short 'Why it matters' section\n"
        "- End with a 'Further reading' list (3 items)\n\n"
        "Return *Markdown only*.\n\n"
        f"NOTES:\n{research_notes}"
    )
    return llm(prompt, temperature=0.4)

def seo_agent(article_md: str) -> dict:
    """Generates SEO frontmatter, FAQ, and JSON-LD (strict JSON)."""
    today = str(date.today())
    prompt = (
        "Return STRICT JSON (no prose) with keys:\n"
        "- title: string (<=60 chars, clear, primary keyword early)\n"
        "- slug: string (lowercase, hyphenated)\n"
        "- meta_description: string (<=155 chars, compelling)\n"
        "- tags: array of 5-7 concise tags (lowercase or Title Case)\n"
        "- faq: array of 3-5 objects {question, answer} (<120 words each)\n"
        "- json_ld: object (schema.org Article), at least:\n"
        "    {\n"
        '      "@context": "https://schema.org",\n'
        '      "@type": "Article",\n'
        '      "headline": <title>,\n'
        '      "description": <meta_description>,\n'
        f'      "datePublished": "{today}",\n'
        f'      "dateModified": "{today}",\n'
        '      "keywords": <comma-separated tags>,\n'
        '      "author": {"@type":"Organization","name":"Your Company"},\n'
        '      "publisher": {"@type":"Organization","name":"Your Company"},\n'
        '      "mainEntityOfPage": {"@type":"WebPage","@id":"https://example.com/<slug>"}\n'
        "    }\n\n"
        "Rules:\n"
        "- Respond with VALID JSON ONLY (no markdown fences).\n\n"
        f"ARTICLE (Markdown):\n{article_md}"
    )
    raw = llm(
        [
            {"role": "system", "content": "You are an SEO editor. Output must be valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    ).strip()

    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "title": "Untitled",
            "slug": "untitled",
            "meta_description": "",
            "tags": ["article"],
            "faq": [],
            "json_ld": {},
        }
    return data

# ----------------------------
# Orchestrator
# ----------------------------
def run_pipeline(pdf_path: str, agents_cfg: dict, tasks_cfg: dict, output_dir: str = "src/data/output", top_k: int = 6, verbose: bool = True) -> str:
    # 0) Load PDF and pre-index (future: retrieval tool)
    pdf_text = load_pdf_text(pdf_path)
    build_store(pdf_text)

    # 1) Researcher
    print("\n===== Researcher Agent =====") if verbose else None
    notes = researcher_agent(pdf_text, top_k=top_k)
    print(notes[:1000] + ("\n... (truncated)\n" if len(notes) > 1000 else "")) if verbose else None

    # 2) Writer
    print("\n===== Writer Agent =====") if verbose else None
    article_md = writer_agent(notes)
    print(article_md[:1000] + ("\n... (truncated)\n" if len(article_md) > 1000 else "")) if verbose else None

    # 3) SEO
    print("\n===== SEO Agent =====") if verbose else None
    meta = seo_agent(article_md)
    print(json.dumps({k: meta.get(k) for k in ("title","slug","meta_description","tags")}, ensure_ascii=False, indent=2)) if verbose else None

    # Ensure slug exists
    if not meta.get("slug"):
        meta["slug"] = make_slug(meta.get("title", "untitled"))

    # Build final Markdown
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{meta['slug']}.md"

    # Frontmatter
    fm = front_matter({
        "title": meta.get("title", "Untitled"),
        "slug": meta.get("slug", "untitled"),
        "meta_description": meta.get("meta_description", ""),
        "tags": meta.get("tags", []),
    })

    # FAQ section
    faq_md = ""
    faq = meta.get("faq") or []
    if faq:
        lines = ["\n\n## FAQs"]
        for item in faq:
            q = (item.get("question") or "").strip()
            a = (item.get("answer") or "").strip()
            if q and a:
                lines.append(f"**Q: {q}**\n\n{a}\n")
        faq_md = "\n".join(lines)

    # JSON-LD block
    json_ld_block = ""
    json_ld = meta.get("json_ld") or {}
    if json_ld:
        json_ld_block = "\n\n<script type=\"application/ld+json\">\n" + json.dumps(json_ld, ensure_ascii=False, indent=2) + "\n</script>"

    out_path.write_text(fm + article_md + faq_md + json_ld_block, encoding="utf-8")
    print(f"\n✅ Wrote: {out_path}")
    return str(out_path)
