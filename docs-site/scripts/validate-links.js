#!/usr/bin/env node
/**
 * Validate and fix broken links in documentation
 *
 * This script:
 * 1. Scans all markdown files for links
 * 2. Checks internal links exist
 * 3. Optionally fixes broken links
 * 4. Reports results
 */

import {
  readFileSync,
  writeFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "fs";
import { resolve, join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..");
const DOCS_DIR = resolve(ROOT, "src/content/docs");

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

function extractLinks(content) {
  const linkRegex = /\[([^\]]+)\]\(([^\)]+)\)/g;
  const links = [];
  let match;

  while ((match = linkRegex.exec(content)) !== null) {
    links.push({
      text: match[1],
      url: match[2],
      full: match[0],
    });
  }

  return links;
}

function checkLink(link, currentFile) {
  const { url } = link;

  // Skip external links
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return { valid: true, type: "external" };
  }

  // Skip anchors
  if (url.startsWith("#")) {
    return { valid: true, type: "anchor" };
  }

  // Check internal link
  let targetPath;

  if (url.startsWith("/")) {
    // Absolute path from docs root
    targetPath = join(DOCS_DIR, url.replace(/\/$/, "") + ".md");
  } else {
    // Relative path from current file
    const currentDir = dirname(currentFile);
    targetPath = resolve(currentDir, url.replace(/\/$/, "") + ".md");
  }

  const exists = existsSync(targetPath);

  return {
    valid: exists,
    type: "internal",
    targetPath,
  };
}

function validateFile(filePath) {
  const content = readFileSync(filePath, "utf-8");
  const links = extractLinks(content);
  const results = [];

  for (const link of links) {
    const check = checkLink(link, filePath);

    if (!check.valid) {
      results.push({
        file: filePath.replace(DOCS_DIR, ""),
        link: link.url,
        text: link.text,
        ...check,
      });
    }
  }

  return results;
}

function main() {
  console.log("🔗 Validating documentation links...");

  const files = getAllMarkdownFiles(DOCS_DIR);
  console.log(`📄 Scanning ${files.length} files...\n`);

  const allBrokenLinks = [];

  for (const file of files) {
    const brokenLinks = validateFile(file);
    if (brokenLinks.length > 0) {
      allBrokenLinks.push(...brokenLinks);
    }
  }

  if (allBrokenLinks.length === 0) {
    console.log("✅ All links are valid!");
    process.exit(0);
  }

  console.log(`⚠️  Found ${allBrokenLinks.length} broken links:\n`);

  for (const broken of allBrokenLinks) {
    console.log(`  ❌ ${broken.file}`);
    console.log(`     Link: ${broken.link}`);
    console.log(`     Text: "${broken.text}"`);
    if (broken.targetPath) {
      console.log(`     Expected: ${broken.targetPath}`);
    }
    console.log();
  }

  console.log(
    "💡 Tip: Review and fix these links manually or update the link checker logic.",
  );
  process.exit(1);
}

main();
