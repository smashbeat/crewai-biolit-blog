from slugify import slugify

def make_slug(title: str) -> str:
    return slugify(title or "untitled")

def front_matter(meta: dict) -> str:
    tags = meta.get("tags", [])
    if isinstance(tags, (list, tuple)):
        tags_line = ", ".join(tags)
    else:
        tags_line = str(tags)
    title = (meta.get("title") or "").replace('"', '\"')
    descr = (meta.get("meta_description") or "").replace('"', '\"')
    slug = meta.get("slug", "")
    return (
        "---\n"
        f'title: "{title}"\n'
        f'description: "{descr}"\n'
        f"slug: {slug}\n"
        f"tags: [{tags_line}]\n"
        "---\n\n"
    )
