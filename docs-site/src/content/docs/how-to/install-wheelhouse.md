---
title: "How-To: Install Hephaestus from a Wheelhouse"
description: "Follow these steps when you want to consume the toolkit in a repository without cloning the full source tree or publishing to PyPI. - Python 3.12 or newer - uv..."
---
Follow these steps when you want to consume the toolkit in a repository without cloning the full
source tree or publishing to PyPI.

## Prerequisites

- Python 3.12 or newer
- [uv](https://github.com/astral-sh/uv) or `pip`
- Access to the GitHub release that provides the wheelhouse archive

## 1. Locate the Wheelhouse Asset

1. Visit the [GitHub Releases](https://github.com/IAmJonoBo/Hephaestus/releases) page.
2. Download the asset named similar to `hephaestus-<version>-wheelhouse.tar.gz`.

## 2. Install via the CLI (Recommended)

The CLI handles download, extraction, checksum verification, and installation.

```bash
uv run hephaestus release install --tag <tag> --cleanup --remove-archive
```

- `--tag <tag>`: optional; defaults to the latest release.
- `--cleanup`: removes the extracted wheelhouse directory after successful install.
- `--remove-archive`: deletes the downloaded archive to keep caches tidy.
- `--manifest-pattern`: override if your release uploads checksum manifests with a different name.
- `--allow-unsigned`: opt out of checksum verification (not recommended except for trusted mirrors).

By default the CLI requires a checksum manifest (matching `*wheelhouse*.sha256`) to be present in the
release and fails closed if verification does not succeed. Store manifests next to the wheelhouse
archives in GitHub Releases to keep installation automated and tamper-evident.

To target a specific repository or self-hosted release mirror, override the repository and asset
pattern:

```bash
uv run hephaestus release install \
  --repository your-org/Hephaestus-fork \
  --asset-pattern "*wheelhouse*.tar.gz"
```

## 3. Install Manually (Fallback)

If you cannot run the CLI, extract and install the wheels yourself:

```bash
mkdir -p wheelhouse
tar -xzf hephaestus-<version>-wheelhouse.tar.gz -C wheelhouse
python -m pip install wheelhouse/*.whl
```

## 4. Verify the Installation

Confirm the CLI is available and report the version:

```bash
python -m hephaestus.cli version
```

or, if you installed with uv:

```bash
uv run hephaestus version
```

## 5. Keep the Toolkit Updated

- Re-run the installation steps whenever a new release lands.
- Automate the process via CI by invoking `hephaestus release install` within your pipeline before
  running CLI workflows.
- Combine with Dependabot or Renovate to receive alerts when new versions are published.

## Troubleshooting

| Symptom                                    | Fix                                                                                    |
| ------------------------------------------ | -------------------------------------------------------------------------------------- |
| `ReleaseError: asset not found`            | Check the `--asset-pattern` or confirm the release tag exists.                         |
| `Checksum manifest could not be found`     | Upload the `*.sha256` manifest next to the wheelhouse asset or use `--allow-unsigned`. |
| `Checksum verification failed`             | Re-upload the wheelhouse and manifest pair; ensure digests match exactly.              |
| `pip` times out or fails due to networking | Pre-download the archive and use the manual install path.                              |
| `wheel directory ... does not exist`       | Ensure the tarball extracted correctly and includes `*.whl` files.                     |
| Import errors after install                | Activate the environment you installed into before running commands                    |
