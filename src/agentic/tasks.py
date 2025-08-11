from crewai import Task
from datetime import datetime

def plan_task(agent, topic):
    return Task(
        description=(
            f"Define angle, audience, search intent, and an H2/H3 outline for: {topic}.\n"
            "Return YAML with keys: angle, audience, intent, entities, outline[]."
        ),
        expected_output="A valid YAML block.",
        agent=agent
    )

def research_task(agent, topic):
    return Task(
        description=(
            f"From the PDF, extract key facts, stats, terms, and cite sources for: {topic}.\n"
            "Return a Markdown doc with sections: Key Points, Entities, Citations (with page if known)."
        ),
        expected_output="Markdown notes with inline citations.",
        agent=agent
    )

def writing_task(agent, topic, slug):
    return Task(
        description=(
            "Write the full article using the outline and research notes. "
            "Include YAML front matter (title, description, date, slug, tags[]) "
            "and a JSON-LD BlogPosting block. Keep tone clear and credible."
        ),
        expected_output=f"Markdown blog post saved-ready. Slug: {slug}",
        agent=agent
    )

def factcheck_task(agent):
    return Task(
        description=(
            "Scan the draft and produce a JSON array: "
            "[{claim, status:'supported'|'uncertain'|'unsupported', sources:[...] }]"
        ),
        expected_output="Valid JSON list of fact checks.",
        agent=agent
    )

def seo_task(agent):
    return Task(
        description=(
            "Refine the title/meta, ensure entity coverage, and validate JSON-LD. "
            "Return a short changelog and final notes for the editor."
        ),
        expected_output="Short Markdown changelog.",
        agent=agent
    )

