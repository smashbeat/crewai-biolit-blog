cat > apps/site/src/utils/slugify.ts <<'TS'
export default function slugify(input: string): string {
  return (input || "")
    .normalize("NFKD")                 // split accents
    .replace(/[\u0300-\u036f]/g, "")   // strip accents
    .toLowerCase()
    .trim()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")       // non-word -> hyphen
    .replace(/^-+|-+$/g, "")           // trim hyphens
    .replace(/-{2,}/g, "-");           // collapse
}
TS

