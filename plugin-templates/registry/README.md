# Marketplace Registry (Curated Templates)

This directory contains curated plugin manifests for the Hephaestus marketplace. Each manifest
is signed, versioned, and subject to explicit trust policies to ensure safe distribution.

Contents:

- `example-plugin.toml`: Marketplace metadata describing the plugin, compatibility, dependencies,
  and entrypoint.
- `example-plugin.sigstore`: Sigstore bundle with digest over the plugin artifact.
- `trust-policy.toml`: Default trust policy requiring signatures from approved identities.

These assets are consumed by `hephaestus.plugins.discover_plugins` when marketplace entries are
referenced in `.hephaestus/plugins.toml`.
