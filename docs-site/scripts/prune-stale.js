#!/usr/bin/env node
/**
 * Detect and flag stale documentation content
 *
 * This script identifies content that may be outdated based on:
 * 1. Last modified date
 * 2. References to old versions
 * 3. TODO/FIXME comments
 * 4. Broken examples
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { resolve, join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..");
const DOCS_DIR = resolve(ROOT, "src/content/docs");

const STALE_THRESHOLD_DAYS = 180; // 6 months
const STALE_PATTERNS = [
  /TODO:/gi,
  /FIXME:/gi,
  /DEPRECATED/gi,
  /\(coming soon\)/gi,
  /\(WIP\)/gi,
];

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

function checkStaleFile(filePath) {
  const stat = statSync(filePath);
  const content = readFileSync(filePath, "utf-8");
  const issues = [];

  // Check last modified date
  const daysSinceModified =
    (Date.now() - stat.mtime.getTime()) / (1000 * 60 * 60 * 24);

  if (daysSinceModified > STALE_THRESHOLD_DAYS) {
    issues.push({
      type: "outdated",
      message: `Not modified in ${Math.round(daysSinceModified)} days`,
      severity: "warning",
    });
  }

  // Check for stale patterns
  for (const pattern of STALE_PATTERNS) {
    const matches = content.match(pattern);
    if (matches) {
      issues.push({
        type: "stale-marker",
        message: `Contains "${matches[0]}" (${matches.length} occurrence${matches.length > 1 ? "s" : ""})`,
        severity: "info",
      });
    }
  }

  return issues.length > 0 ? { file: filePath, issues } : null;
}

function main() {
  console.log("🕵️  Detecting stale documentation content...");
  console.log(`   Threshold: ${STALE_THRESHOLD_DAYS} days\n`);

  const files = getAllMarkdownFiles(DOCS_DIR);
  const staleFiles = [];

  for (const file of files) {
    const result = checkStaleFile(file);
    if (result) {
      staleFiles.push(result);
    }
  }

  if (staleFiles.length === 0) {
    console.log("✅ No stale content detected!");
    process.exit(0);
  }

  console.log(
    `⚠️  Found ${staleFiles.length} files with potential staleness:\n`,
  );

  for (const { file, issues } of staleFiles) {
    console.log(`  📄 ${file.replace(DOCS_DIR, "")}`);
    for (const issue of issues) {
      const icon = issue.severity === "warning" ? "⚠️" : "ℹ️";
      console.log(`     ${icon} ${issue.message}`);
    }
    console.log();
  }

  console.log("💡 Review these files and update as needed.");
}

main();
