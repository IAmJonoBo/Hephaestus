# Astro Starlight Documentation System - Quick Start

## 📖 Documentation Site

**Live Site:** https://iamjonobo.github.io/Hephaestus/

## 🚀 Quick Commands

```bash
# View documentation locally
cd docs-site
npm install
npm run dev           # http://localhost:4321

# Update auto-generated content
npm run update-all    # Updates CLI ref, API docs, changelog, versions

# Run quality checks
npm run validate-all  # Validates links, examples, detects stale content

# Build for production
npm run build         # Output: docs-site/dist/
```

## 🤖 Automation Features

### Daily Scheduled Updates (2 AM UTC)

The documentation automatically updates itself with:

1. **CLI Reference** - From `hephaestus schema` output
2. **API Documentation** - From code annotations
3. **Changelog** - Synced from root `CHANGELOG.md`
4. **Version References** - From `pyproject.toml`

### Validation on Every PR

- ✅ Link validation (internal & external)
- ✅ Code example syntax checking
- ✅ Stale content detection (180+ days)
- ✅ TypeScript type checking
- ✅ Sitemap generation
- ✅ Search index building

## 📁 Directory Structure

```
docs-site/
├── src/
│   ├── content/
│   │   ├── docs/           # All documentation markdown files
│   │   │   ├── index.md    # Home page
│   │   │   ├── tutorials/  # Learning-oriented content
│   │   │   ├── how-to/     # Task-oriented guides
│   │   │   ├── explanation/ # Understanding-oriented content
│   │   │   ├── reference/  # Information-oriented reference
│   │   │   └── adr/        # Architecture Decision Records
│   │   └── config.ts       # Content collection schema
│   ├── styles/
│   │   └── custom.css      # Custom styling
│   └── assets/
│       └── logo.svg        # Hephaestus logo
├── scripts/                # Automation scripts
│   ├── update-cli-reference.js
│   ├── update-api-docs.js
│   ├── sync-changelog.js
│   ├── sync-version.js
│   ├── validate-links.js
│   ├── validate-examples.js
│   └── prune-stale.js
├── astro.config.mjs        # Starlight configuration
├── package.json            # Dependencies and scripts
└── README.md               # Detailed documentation
```

## ✍️ Adding New Documentation

1. Create markdown file in appropriate category under `src/content/docs/`
2. Add frontmatter:

   ```markdown
   ---
   title: "Your Page Title"
   description: "Brief description for SEO"
   ---

   Your content here...
   ```

3. Test locally: `npm run dev`
4. Validate: `npm run validate-all`
5. Commit and push - CI will handle the rest!

## 🎯 Diátaxis Structure

Documentation follows the [Diátaxis framework](https://diataxis.fr/):

- **Tutorials** - Step-by-step learning experiences
- **How-To Guides** - Recipes for solving specific problems
- **Explanation** - Understanding-oriented discussions
- **Reference** - Technical descriptions and specifications

## 🔧 Maintenance

### Running Automation Scripts Manually

```bash
cd docs-site

# Individual updates
npm run update-cli-reference  # Update CLI docs
npm run update-api-docs       # Update API reference
npm run sync-changelog        # Sync changelog
npm run sync-version          # Update version refs

# Individual validations
npm run validate-links        # Check all links
npm run validate-examples     # Validate code examples
npm run prune-stale          # Detect stale content
```

### Troubleshooting

**Build fails?**

- Check Node.js version: `node --version` (need 20+)
- Clean install: `rm -rf node_modules package-lock.json && npm install`
- Check for TypeScript errors: `npm run check`

**Content not showing?**

- Ensure frontmatter is properly formatted
- Check file is in `src/content/docs/`
- Verify no validation errors in build output

**Links broken?**

- Run `npm run validate-links`
- Use `/path/to/page/` format (with trailing slash)
- For internal docs, use Starlight's slug format

## 📊 Quality Metrics

Current status:

- ✅ 46 pages built
- ✅ 45 pages indexed
- ✅ 4,513 words indexed
- ✅ 0 broken links
- ✅ Sitemap generated
- ✅ Search working

## 🔗 Important Links

- **Documentation Site:** https://iamjonobo.github.io/Hephaestus/
- **Maintenance Guide:** https://iamjonobo.github.io/Hephaestus/explanation/docs-maintenance/
- **ADR 0007 (Migration Details):** https://iamjonobo.github.io/Hephaestus/adr/0007-astro-starlight-migration/
- **Astro Starlight Docs:** https://starlight.astro.build/
- **Diátaxis Framework:** https://diataxis.fr/

## 🆘 Getting Help

- **Documentation Issues:** File issue with `documentation` label
- **Automation Issues:** File issue with `automation` label
- **CI/CD Issues:** File issue with `ci` label

Include:

1. Steps to reproduce
2. Expected vs actual behavior
3. Relevant logs/screenshots
4. Environment details

---

**Migration Date:** January 2025  
**Previous System:** MkDocs Material (archived)  
**Why:** Frontier-grade automation, self-updating content, better DX
