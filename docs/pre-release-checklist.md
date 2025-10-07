# Pre-Release Automation Checklist

Use this quick checklist before cutting a release to ensure the repository is pristine and all automation hooks have run:

1. **Confirm automation parity**
   - [ ] `uv sync --extra dev --extra qa`
   - [ ] `uv run pre-commit run --all-files`
   - [ ] `uv run hephaestus cleanup --deep-clean`

2. **Verify quality gates locally**
   - [ ] `uv run ruff check .`
   - [ ] `uv run mypy src tests`
   - [ ] `uv run pytest`

3. **Run packaging sanity checks**
   - [ ] `uv run hephaestus cleanup --deep-clean` (repeat to confirm clean tree)
   - [ ] Remove temporary artefacts (`dist/`, `build/`, coverage caches) if present—these
         directories are `.gitignore`d but cleaning them locally keeps release diffs obvious
   - [ ] Confirm the latest release will have a wheelhouse by spot-checking the `Build Wheelhouse`
         workflow and ensuring the zipped artefact downloads successfully
   - [ ] Dry-run the installer with `uv run hephaestus release install --cleanup --remove-archive`
         against the latest tag to verify the wheelhouse installs cleanly from GitHub Releases

4. **Review documentation**
   - [ ] Update `docs/lifecycle.md` and `README.md` if automation changed
   - [ ] Record release notes / changelog summary

5. **Tag and release**
   - When ready, push to `main`—the release workflow will perform the final cleanup sweep and tag automatically.
