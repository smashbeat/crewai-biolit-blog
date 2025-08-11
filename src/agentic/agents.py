from crewai import Agent
import os

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def strategist():
    return Agent(
        role="Content Strategist",
        goal=("Turn a single PDF into an SEO-ready plan: angle, audience, "
              "search intent, headings, and entity coverage."),
        backstory=("You’re an expert in SEO content strategy and topical authority."),
        allow_delegation=False,
        model=OPENAI_MODEL,
        verbose=False,
    )

def researcher(rag_tool, web_tool=None):
    tools = [rag_tool] + ([web_tool] if web_tool else [])
    return Agent(
        role="Biomedical Researcher",
        goal=("Extract accurate facts, stats, entities and citations from the PDF "
              "and optionally the open web; produce concise notes with source attributions."),
        backstory=("You love rigor, citations, and avoiding speculation."),
        tools=tools,
        allow_delegation=False,
        model=OPENAI_MODEL,
        verbose=False,
    )

def writer():
    return Agent(
        role="Senior Technical Writer",
        goal=("Write a clear, engaging blog post with front matter and JSON-LD "
              "that targets the defined search intent."),
        backstory=("You write for humans first, search engines second."),
        allow_delegation=False,
        model=OPENAI_MODEL,
        verbose=False,
    )

def fact_checker(rag_tool, web_tool=None):
    tools = [rag_tool] + ([web_tool] if web_tool else [])
    return Agent(
        role="Fact Checker",
        goal=("Validate claims, flag uncertainties, and attach sources. "
              "Return a machine-readable verification JSON."),
        backstory=("Skeptical by nature; you verify everything."),
        tools=tools,
        allow_delegation=False,
        model=OPENAI_MODEL,
        verbose=False,
    )

def seo_finisher():
    return Agent(
        role="SEO & Schema Finisher",
        goal=("Refine title/meta, ensure entity coverage, and validate JSON-LD, "
              "then finalize deliverables."),
        backstory=("You ensure search readiness & structured data correctness."),
        allow_delegation=False,
        model=OPENAI_MODEL,
        verbose=False,
    )

