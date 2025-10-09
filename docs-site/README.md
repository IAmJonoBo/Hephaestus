# Docs Site

This directory contains the Astro Starlight documentation site for Hephaestus.

## Structure

- `src/content/docs/` - All documentation markdown files (auto-migrated from `../docs/`)
- `scripts/` - Automation scripts for self-updating documentation
- `public/` - Static assets
- `astro.config.mjs` - Starlight configuration
- `package.json` - Node dependencies and automation scripts

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Automation Scripts

### Content Updates (Auto-run in CI)

- `npm run update-cli-reference` - Generate CLI reference from Typer schemas
- `npm run update-api-docs` - Generate API docs from code annotations
- `npm run sync-changelog` - Sync changelog from root CHANGELOG.md
- `npm run sync-version` - Update version references from pyproject.toml
- `npm run update-all` - Run all update scripts

### Validation (Auto-run in CI)

- `npm run validate-links` - Check and fix broken links
- `npm run validate-examples` - Validate code examples
- `npm run prune-stale` - Detect and flag stale content
- `npm run validate-all` - Run all validation scripts

## CI/CD

The documentation is automatically:

1. Built and deployed to GitHub Pages on every push to `main`
2. Validated for broken links, stale content, and example correctness
3. Updated with latest CLI schemas, API docs, and version information
4. Checked for accessibility and search indexing

## Migration from MkDocs

The content was automatically migrated from MkDocs using `scripts/migrate-from-mkdocs.py`, which:

- Converted MkDocs-style navigation to Starlight sidebar
- Transformed internal links
- Added proper frontmatter
- Preserved Diátaxis structure
- Maintained all content and formatting
