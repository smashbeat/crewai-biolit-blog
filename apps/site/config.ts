import { defineCollection, z } from "astro:content";

const posts = defineCollection({
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    description: z.string().max(200).default(""),
    tags: z.array(z.string()).default([]),
    date: z.string().optional(),   // or z.date()
    draft: z.boolean().default(false),
  })
});

export const collections = { posts };

