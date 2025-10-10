---
title: "Documentation Maintenance Guide"
description: "How to maintain and update the Hephaestus documentation site"
---

## Overview

The Hephaestus documentation is built with Astro Starlight and features extensive automation for self-updating content. This guide explains how the system works and how to maintain it.

## Architecture

### Components

```
┌─────────────────────────────────────────────────┐
│            Documentation System                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Source Content (docs-site/src/content/docs/)   │
│  ↓                                               │
│  Automation Scripts (docs-site/scripts/)        │
│  ↓                                               │
│  Auto-Generated Content                         │
│  ↓                                               │
│  Astro Build                                    │
│  ↓                                               │
│  GitHub Pages                                   │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Key Directories

- `docs-site/src/content/docs/` - All documentation markdown files
- `docs-site/scripts/` - Automation scripts for content updates
- `docs-site/public/` - Static assets (images, etc.)
- `.github/workflows/docs.yml` - CI/CD pipeline

## Automation System

### Daily Scheduled Updates (2 AM UTC)

The documentation automatically updates itself daily with:

1. **CLI Reference** - Generated from `hephaestus schema` output
2. **API Documentation** - Generated from code annotations
3. **Changelog** - Synced from root `CHANGELOG.md`
4. **Version References** - Updated from `pyproject.toml`

### Validation Checks (Every PR/Push)

1. **Link Validation** - Checks all internal and external links
2. **Example Validation** - Validates code examples for syntax
3. **Stale Content Detection** - Flags content not updated in 180+ days
4. **Type Checking** - Validates TypeScript/Astro components

## Manual Operations

### Local Development

```bash
# Navigate to docs site
cd docs-site

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Open browser to http://localhost:4321
```

### Running Automation Scripts

```bash
cd docs-site

# Update all auto-generated content
npm run update-all

# Run all validation checks
npm run validate-all

# Individual scripts
npm run update-cli-reference  # Update CLI docs
npm run update-api-docs       # Update API reference
npm run sync-changelog        # Sync changelog
npm run sync-version          # Update version references
npm run validate-links        # Check links
npm run validate-examples     # Validate code examples
npm run prune-stale          # Detect stale content
```

### Adding New Documentation

1. **Create Markdown File**

   Place file in appropriate Diátaxis category:
   - `tutorials/` - Learning-oriented content
   - `how-to/` - Task-oriented guides
   - `explanation/` - Understanding-oriented content
   - `reference/` - Information-oriented reference

2. **Add Frontmatter**

   ```markdown
   ---
   title: "Your Page Title"
   description: "Brief description for SEO and navigation"
   ---

   Your content here...
   ```

3. **Update Navigation**

   Edit `docs-site/astro.config.mjs` sidebar configuration if needed.

4. **Test Locally**

   ```bash
   cd docs-site
   npm run dev
   ```

5. **Validate**

   ```bash
   npm run validate-all
   ```

### Updating Automation Scripts

Scripts are located in `docs-site/scripts/`. Each script:

- Is a Node.js module (`.js` file)
- Has a corresponding npm script in `package.json`
- Should handle errors gracefully
- Should log progress for CI visibility

Example script structure:

```javascript
#!/usr/bin/env node
import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

function main() {
  console.log("🔄 Starting update...");

  try {
    // Your automation logic here

    console.log("✅ Update complete!");
  } catch (error) {
    console.error("❌ Error:", error.message);
    process.exit(1);
  }
}

main();
```

## CI/CD Pipeline

### Workflow: `.github/workflows/docs.yml`

**Triggers:**

- Push to `main` (paths: `docs-site/**`, `docs/**`)
- Pull requests
- Manual dispatch
- Daily schedule (2 AM UTC)

**Jobs:**

1. **update-content** - Run automation scripts, commit changes
2. **validate** - Run validation checks
3. **build** - Build Astro site, upload artifacts
4. **deploy** - Deploy to GitHub Pages (main branch only)
5. **preview** - Comment on PRs with preview info

### Monitoring

Check workflow runs at:
`https://github.com/IAmJonoBo/Hephaestus/actions/workflows/docs.yml`

Common issues:

- **Build failures**: Check Node.js dependencies, Astro config
- **Validation failures**: Review broken links, invalid examples
- **Deployment failures**: Check GitHub Pages settings, permissions

## Content Guidelines

### Diátaxis Principles

Follow the [Diátaxis framework](https://diataxis.fr/):

- **Tutorials**: Step-by-step lessons for beginners
- **How-To Guides**: Recipes for solving specific problems
- **Explanation**: Understanding-oriented discussions
- **Reference**: Technical descriptions (CLI, API, etc.)

### Style Guidelines

1. **Use Active Voice**: "Run the command" not "The command should be run"
2. **Be Concise**: Remove unnecessary words
3. **Code Examples**: Always test your examples
4. **Links**: Use descriptive link text, not "click here"
5. **Headings**: Use sentence case, not title case

### Markdown Conventions

- Use `:::note` for callouts/admonitions
- Use `:::warning` for warnings
- Use `:::tip` for helpful tips
- Use triple backticks with language for code blocks
- Use tables for structured data
- Use relative links for internal pages

### Auto-Generated Content

Pages with auto-generated content should have a note:

```markdown
:::note[Auto-generated]
This page is automatically generated from [source].
Last updated: [timestamp]
:::
```

## Troubleshooting

### Links Not Working

1. Run link validator: `npm run validate-links`
2. Check link format: `/path/to/page/` (with trailing slash)
3. Ensure target file exists in `src/content/docs/`

### Build Failures

1. Check Node.js version: `node --version` (should be 20+)
2. Clean install: `rm -rf node_modules package-lock.json && npm install`
3. Check for TypeScript errors: `npm run check`
4. Review build logs in CI

### Content Not Updating

1. Check if automation script ran: Review CI logs
2. Manually run script: `npm run update-cli-reference`
3. Check source data (pyproject.toml, schemas, etc.)
4. Verify permissions for committing changes

### Stale Content Warnings

Review files flagged by `npm run prune-stale`:

1. Update content if outdated
2. Remove if no longer needed
3. Add to exclusion list if intentionally old (historical docs)

## Maintenance Schedule

### Daily (Automated)

- Auto-update generated content
- Deploy to GitHub Pages

### Weekly

- Review stale content warnings
- Check for broken links
- Update dependencies

### Monthly

- Review automation script effectiveness
- Update documentation style guide
- Check analytics (if enabled)

### Quarterly

- Comprehensive documentation review
- Update ADR 0007 if architecture changed
- Review and update this maintenance guide

## Emergency Procedures

### Rollback Documentation

If deployed docs are broken:

1. Revert the commit that caused the issue
2. Push to trigger redeployment
3. Monitor deployment at GitHub Actions

### Disable Automation

If automation is causing issues:

1. Edit `.github/workflows/docs.yml`
2. Comment out problematic jobs
3. Commit and push
4. Fix scripts locally
5. Re-enable automation

## References

- [Astro Documentation](https://docs.astro.build/)
- [Starlight Guide](https://starlight.astro.build/)
- [Diátaxis Framework](https://diataxis.fr/)
- [ADR 0007: Astro Starlight Migration](/adr/0007-astro-starlight-migration/)
- [CONTRIBUTING.md](https://github.com/IAmJonoBo/Hephaestus/blob/main/CONTRIBUTING.md)

## Getting Help

- **Documentation Issues**: File issue with `documentation` label
- **Automation Issues**: File issue with `automation` label
- **CI/CD Issues**: File issue with `ci` label

When reporting issues, include:

1. Steps to reproduce
2. Expected vs actual behavior
3. Relevant logs/screenshots
4. Environment details (Node.js version, etc.)
