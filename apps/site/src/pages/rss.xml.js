import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

export async function GET(context) {
  const posts = (await getCollection("posts")).filter(p => !p.data.draft);
  return rss({
    title: "Biolit",
    description: "Readable, SEO-ready posts from PDFs.",
    site: context.site, // uses astro.config.mjs site
    items: posts.map(p => ({
      link: `/posts/${p.data.slug}/`,
      title: p.data.title,
      description: p.data.description,
      pubDate: p.data.date ? new Date(p.data.date) : undefined,
    })),
  });
}

