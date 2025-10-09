# ADR Migration Notice

📖 **The Architecture Decision Records have been migrated to Astro Starlight!**

## New Location

**View the ADRs at:** https://iamjonobo.github.io/Hephaestus/adr/

**Source files:** `docs-site/src/content/docs/adr/`

## What Changed?

As part of the Astro Starlight migration (ADR-0007), all documentation including ADRs has moved to the new documentation site with:

- **Self-Updating**: Auto-generated content updates daily
- **Modern Stack**: Built with Astro Starlight for better performance
- **Full Search**: Powered by Pagefind for instant results
- **Better Navigation**: Integrated with the complete documentation structure

## For Contributors

When updating ADRs, please edit the files in `docs-site/src/content/docs/adr/`.

The files in this directory (`docs/adr/`) are maintained for backward compatibility but may be out of sync. Always refer to the docs-site version as the source of truth.

### Local Development

```bash
cd docs-site
npm install
npm run dev          # Start dev server at http://localhost:4321
```

## See Also

- [ADR-0007: Astro Starlight Migration](../../docs-site/src/content/docs/adr/0007-astro-starlight-migration.md)
- [Documentation Migration Guide](../MIGRATION.md)
- [Docs Site README](../../docs-site/README.md)
