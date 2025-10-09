# Documentation Migration Notice

📖 **The documentation has been migrated to Astro Starlight!**

## New Documentation Site

**View the documentation at:** https://iamjonobo.github.io/Hephaestus/

## What Changed?

The documentation system has been upgraded with frontier-grade automation:

- **Self-Updating**: CLI references, API docs, and versions auto-update daily
- **Automated Quality**: Link validation, example testing, stale content detection
- **Modern Stack**: Built with Astro Starlight for better performance and DX
- **Full Search**: Powered by Pagefind for instant results

## For Contributors

Documentation source files have moved to `docs-site/src/content/docs/`.

### Local Development

```bash
cd docs-site
npm install
npm run dev          # Start dev server at http://localhost:4321
npm run update-all   # Update auto-generated content
npm run validate-all # Run quality checks
```

## Migration Details

- **When**: January 2025
- **Why**: See [ADR 0007](https://iamjonobo.github.io/Hephaestus/adr/0007-astro-starlight-migration/)
- **Old System**: MkDocs Material (archived as `mkdocs.yml.archived`)
- **New System**: Astro Starlight with extensive automation

## Legacy Files

This `docs/` directory is preserved for reference but is no longer the active documentation source. All new documentation should be added to `docs-site/src/content/docs/`.

---

For questions or issues, see the [Documentation Maintenance Guide](https://iamjonobo.github.io/Hephaestus/explanation/docs-maintenance/).
