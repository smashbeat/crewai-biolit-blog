import os, json, re
from datetime import datetime
from crewai import Crew, Process
from .agents import strategist, researcher, writer, fact_checker, seo_finisher
from .tools import pdf_rag_search, json_validate, yaml_validate
from .tasks import plan_task, research_task, writing_task, factcheck_task, seo_task

OUTDIR = "src/data/output"

def _safe_slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def save(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def run_agentic(topic: str, pdf_txt_path: str):
    # expose PDF cache for the tool
    os.environ["PDF_TXT_CACHE"] = pdf_txt_path

    strat = strategist()
    res = researcher(pdf_rag_search)
    wr = writer()
    fc = fact_checker(pdf_rag_search)
    fin = seo_finisher()

    slug = _safe_slug(topic)
    date = datetime.utcnow().date().isoformat()

    crew = Crew(
        agents=[strat, res, wr, fc, fin],
        tasks=[
            plan_task(strat, topic),
            research_task(res, topic),
            writing_task(wr, topic, slug),
            factcheck_task(fc),
            seo_task(fin),
        ],
        process=Process.sequential,
        verbose=False,
    )

    results = crew.kickoff()

    # Pull artifacts from each task’s output text (CrewAI returns a list)
    plan_yaml = results[0].raw if hasattr(results[0], "raw") else str(results[0])
    research_md = results[1].raw if hasattr(results[1], "raw") else str(results[1])
    post_md = results[2].raw if hasattr(results[2], "raw") else str(results[2])
    facts_json = results[3].raw if hasattr(results[3], "raw") else str(results[3])
    seo_notes = results[4].raw if hasattr(results[4], "raw") else str(results[4])

    # Validate JSON/YAML lightly
    if "error:" in yaml_validate(plan_yaml):
        plan_yaml = f"# YAML validation failed; raw output kept\n{plan_yaml}"
    if "error:" in json_validate(facts_json):
        facts_json = json.dumps({"error": "invalid json from fact checker", "raw": facts_json}, indent=2)

    # Optional: extract image prompt ideas from the research/posts
    image_prompts = (
        "Generate 3 image prompts that would help illustrate the post. "
        "Style: photorealistic or schematic as appropriate. Include subject, setting, lighting, and angle."
    )

    base = os.path.join(OUTDIR, slug)
    paths = {
        "plan": save(f"{base}-plan.yaml", plan_yaml),
        "research": save(f"{base}-research.md", research_md),
        "post": save(f"{base}-post.md", post_md),
        "facts": save(f"{base}-facts.json", facts_json if isinstance(facts_json, str) else json.dumps(facts_json, indent=2)),
        "seo": save(f"{base}-seo-notes.md", seo_notes),
        "image_prompts": save(f"{base}-image-prompts.md", image_prompts),
    }
    return paths

