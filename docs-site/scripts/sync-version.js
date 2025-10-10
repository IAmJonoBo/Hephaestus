#!/usr/bin/env node
/**
 * Sync version information from pyproject.toml
 *
 * Updates all version references in documentation to match the current version.
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from "fs";
import { resolve, join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..");
const DOCS_DIR = resolve(ROOT, "src/content/docs");
const PYPROJECT = resolve(ROOT, "../pyproject.toml");

function extractVersion() {
  const content = readFileSync(PYPROJECT, "utf-8");
  const match = content.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) {
    throw new Error("Could not extract version from pyproject.toml");
  }
  return match[1];
}

function getAllMarkdownFiles(dir) {
  const files = [];

  function walk(currentDir) {
    const items = readdirSync(currentDir);

    for (const item of items) {
      const fullPath = join(currentDir, item);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        walk(fullPath);
      } else if (item.endsWith(".md")) {
        files.push(fullPath);
      }
    }
  }

  walk(dir);
  return files;
}

function updateVersionReferences(filePath, version) {
  let content = readFileSync(filePath, "utf-8");
  let updated = false;

  // Pattern: v0.1.0, version 0.1.0, etc.
  const versionPattern = /v?\d+\.\d+\.\d+/g;

  // Update version in common patterns
  const patterns = [
    {
      regex: /hephaestus-toolkit==\d+\.\d+\.\d+/g,
      replacement: `hephaestus-toolkit==${version}`,
    },
    {
      regex: /"version":\s*"\d+\.\d+\.\d+"/g,
      replacement: `"version": "${version}"`,
    },
    { regex: /Version:\s*\d+\.\d+\.\d+/gi, replacement: `Version: ${version}` },
  ];

  for (const { regex, replacement } of patterns) {
    const newContent = content.replace(regex, replacement);
    if (newContent !== content) {
      content = newContent;
      updated = true;
    }
  }

  if (updated) {
    writeFileSync(filePath, content, "utf-8");
    return true;
  }

  return false;
}

function main() {
  console.log("🔄 Syncing version information...");

  const version = extractVersion();
  console.log(`📦 Current version: ${version}`);

  const files = getAllMarkdownFiles(DOCS_DIR);
  console.log(`📄 Found ${files.length} markdown files`);

  let updatedCount = 0;
  for (const file of files) {
    if (updateVersionReferences(file, version)) {
      console.log(`  ✓ Updated ${file.replace(DOCS_DIR, "")}`);
      updatedCount++;
    }
  }

  console.log(`✅ Version sync complete! Updated ${updatedCount} files.`);
}

main();
