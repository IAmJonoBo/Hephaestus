# Operations

## TurboRepo Release Tracking

- `turborepo-release.json` records the upstream TurboRepo release currently sanctioned by the toolkit.
- The `TurboRepo Release Monitor` GitHub Actions workflow runs daily and on demand to compare the recorded tag against the latest upstream release.
- When a newer tag is published, the workflow opens an issue titled `Track TurboRepo release <tag>`. Update the toolkit, bump the `tracked_tag`, and refresh `checked_at` to acknowledge the release.
