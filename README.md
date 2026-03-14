# Freed Solutions

Fractional data and systems consulting for the cannabis industry.

**Website:** [freedsolutions.com](https://www.freedsolutions.com)  
**Contact:** [Book a call](https://calendly.com/freedsolutions/30min)

## Repo Structure

```text
FreedSolutions/
|- index.html                    # Landing page (GitHub Pages)
|- CLAUDE.md                     # AI workflow config and project routing
|- CNAME                         # Custom domain (freedsolutions.com)
|- brand/                        # Brand assets - local only (.gitignore)
|- projects/
|  |- linkedin-carousel/         # LinkedIn carousel slide designer
|- ops/                          # Internal ops, migration docs, and private service scaffolds
```

### Projects

- **[LinkedIn Carousel](projects/linkedin-carousel/)** - A single-page React app that renders LinkedIn carousel slides to HTML5 Canvas for pixel-accurate export. See its own [CLAUDE.md](projects/linkedin-carousel/CLAUDE.md) for development workflow.
- **[LinkedIn CRM Service](ops/linkedin-crm-service/)** - A private Node service scaffold for LinkedIn OAuth to Notion CRM intake and approval. Keep this deployed separately from the static site.

### Global Assets

- `index.html` - Landing page deployed via GitHub Pages
- `brand/` - Logo, resumes, and other brand assets (local only, not tracked)
- `ops/` - Internal operations, migration prompts, automation scripts, and private service scaffolds
