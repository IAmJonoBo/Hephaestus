#!/usr/bin/env node
/**
 * Sync CHANGELOG.md to documentation
 *
 * Creates a changelog page from the root CHANGELOG.md file.
 */

import { readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..");
const CHANGELOG_SRC = resolve(ROOT, "../CHANGELOG.md");
const CHANGELOG_DEST = resolve(ROOT, "src/content/docs/reference/changelog.md");

function main() {
  console.log("🔄 Syncing CHANGELOG...");

  let content = readFileSync(CHANGELOG_SRC, "utf-8");

  // Add frontmatter
  const frontmatter = `---
title: "Changelog"
description: "Version history and release notes for Hephaestus toolkit"
---

:::note[Auto-synced]
This page is automatically synchronized from the root CHANGELOG.md file.
Last synced: ${new Date().toISOString()}
:::

`;

  content = frontmatter + content;

  writeFileSync(CHANGELOG_DEST, content, "utf-8");

  console.log(`✅ Changelog synced to ${CHANGELOG_DEST}`);
}

main();
