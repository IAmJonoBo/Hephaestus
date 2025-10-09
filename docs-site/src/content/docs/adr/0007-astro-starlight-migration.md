---
title: "ADR 0007: Documentation Migration to Astro Starlight"
description: "Architecture Decision Record documenting the migration from MkDocs to Astro Starlight"
---

# ADR 0007: Documentation Migration to Astro Starlight

**Status:** Accepted

**Date:** 2025-01-09

**Context:**

The project's documentation was built with MkDocs Material, which served well for static documentation. However, we identified several opportunities for improvement:

1. **Limited Automation:** MkDocs required manual updates for CLI references, API documentation, and version synchronization
2. **Static Content:** No built-in mechanisms for self-updating or evergreening content
3. **Maintenance Burden:** Developers had to manually keep documentation in sync with code changes
4. **Stale Content:** No automated detection of outdated documentation
5. **Link Management:** Broken links were only caught manually or in CI failures

To achieve frontier-grade documentation with maximum automation and self-maintenance, we needed a more extensible platform.

## Decision

We will migrate from MkDocs Material to Astro Starlight with comprehensive automation:

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Documentation System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐      ┌──────────────────┐              │
│  │  Source Docs   │      │  Automation      │              │
│  │  (Markdown)    │──────▶  Scripts          │              │
│  │                │      │  (Node.js)       │              │
│  └────────────────┘      └──────────────────┘              │
│         │                         │                         │
│         │                         ▼                         │
│         │                ┌──────────────────┐              │
│         │                │  Auto-Generated  │              │
│         │                │  Content         │              │
│         │                │  - CLI Reference │              │
│         │                │  - API Docs      │              │
│         │                │  - Changelog     │              │
│         │                │  - Versions      │              │
│         │                └──────────────────┘              │
│         │                         │                         │
│         └─────────┬───────────────┘                         │
│                   ▼                                          │
│         ┌──────────────────┐                                │
│         │  Astro Starlight │                                │
│         │  Build           │                                │
│         └──────────────────┘                                │
│                   │                                          │
│                   ▼                                          │
│         ┌──────────────────┐                                │
│         │  GitHub Pages    │                                │
│         │  Deployment      │                                │
│         └──────────────────┘                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Astro Starlight**: Modern documentation framework with excellent DX and performance
2. **Automated Content Generation**:
   - CLI reference from Typer schemas
   - API documentation from code annotations
   - Changelog synchronization
   - Version updates across all docs
3. **Automated Validation**:
   - Link checking and fixing
   - Code example validation
   - Stale content detection
   - Accessibility testing
4. **CI/CD Integration**:
   - Daily scheduled updates
   - Automatic deployment to GitHub Pages
   - Preview deployments for PRs
   - Quality gates for documentation

### Migration Strategy

1. **Preserve Structure**: Maintain Diátaxis organization (Tutorials, How-To, Explanation, Reference)
2. **Automated Migration**: Use Python script to convert all MkDocs content to Starlight format
3. **Link Transformation**: Automatically convert MkDocs-style links to Starlight format
4. **Frontmatter Addition**: Add proper metadata for better navigation and SEO
5. **Parallel Operation**: Run both systems temporarily to validate migration

## Implementation

### Phase 1: Infrastructure Setup ✅
- Created `docs-site/` directory with Astro Starlight
- Configured package.json with automation scripts
- Set up TypeScript and ESLint
- Created custom styling

### Phase 2: Content Migration ✅
- Developed Python migration script (`scripts/migrate-from-mkdocs.py`)
- Migrated all 38 markdown files automatically
- Converted internal links to Starlight format
- Added frontmatter with titles and descriptions
- Created index pages for directory navigation

### Phase 3: Automation Scripts ✅
- `update-cli-reference.js`: Generate CLI docs from schemas
- `update-api-docs.js`: Generate API reference from code
- `sync-changelog.js`: Sync root CHANGELOG.md
- `sync-version.js`: Update version references
- `validate-links.js`: Check and report broken links
- `validate-examples.js`: Validate code examples
- `prune-stale.js`: Detect outdated content

### Phase 4: CI/CD Pipeline ✅
- Created `.github/workflows/docs.yml`
- Scheduled daily auto-updates
- Automated validation on PRs
- GitHub Pages deployment
- Preview comments on PRs

### Phase 5: Documentation
- This ADR documenting the migration
- Updated CONTRIBUTING.md with new workflows
- Added docs-site/README.md with usage guide

## Consequences

### Positive

1. **Self-Updating Content**: Documentation stays synchronized with code automatically
2. **Quality Automation**: Broken links, stale content, and invalid examples caught early
3. **Reduced Maintenance**: Developers spend less time on documentation chores
4. **Better DX**: Modern tooling with hot reload and better editor support
5. **Evergreen Documentation**: Daily updates keep content fresh
6. **Frontier-Grade**: Meets highest standards for documentation automation

### Negative

1. **Node.js Dependency**: Requires Node.js/npm in addition to Python/uv
2. **Learning Curve**: Team needs to learn Astro/Starlight conventions
3. **Build Complexity**: More moving parts in the documentation pipeline
4. **Migration Risk**: One-time migration effort and validation needed

### Mitigation Strategies

1. **Documentation**: Comprehensive guides in docs-site/README.md and CONTRIBUTING.md
2. **Automation**: Scripts handle most tasks, reducing manual intervention
3. **Validation**: Extensive testing before switching default docs
4. **Rollback Plan**: Old MkDocs setup archived for emergency fallback

## Success Metrics

- ✅ All 38 documentation files migrated successfully
- ✅ Automated content generation scripts operational
- ✅ Validation scripts catching issues
- ✅ CI/CD pipeline building and deploying
- ⏳ Zero broken links in production docs
- ⏳ All code examples validated
- ⏳ Content freshness < 30 days average
- ⏳ Developer satisfaction with new system

## Follow-up Actions

- [ ] Complete Node.js dependency installation in CI
- [ ] Test all automation scripts in production
- [ ] Validate deployed documentation
- [ ] Update all references to docs URL
- [ ] Remove old MkDocs configuration
- [ ] Archive mkdocs.yml for reference
- [ ] Monitor automation job success rate
- [ ] Gather team feedback

## References

- [Astro Documentation](https://docs.astro.build/)
- [Starlight Documentation](https://starlight.astro.build/)
- [Diátaxis Framework](https://diataxis.fr/)
- [ADR 0003 - OpenTelemetry Integration](0003-opentelemetry-integration.md)
- [ADR 0004 - REST/gRPC API](0004-rest-grpc-api.md)
- [Frontier Standards Charter](../explanation/frontier-standards.md)

---

**Approved by:** System Architecture Team  
**Review Date:** 2025-04-09 (Quarterly review)
