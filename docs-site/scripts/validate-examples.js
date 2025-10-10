#!/usr/bin/env node
/**
 * Validate code examples in documentation
 *
 * This script extracts code blocks from markdown files and validates them
 * where possible (syntax checking, import validation, etc.)
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { resolve, join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

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

function extractCodeBlocks(content, filePath) {
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  const blocks = [];
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    blocks.push({
      language: match[1] || "text",
      code: match[2],
      file: filePath,
    });
  }

  return blocks;
}

function validatePythonSyntax(code) {
  // Basic Python syntax checks
  const issues = [];

  // Check for common issues
  if (
    code.includes("hephaestus") &&
    !code.includes("import") &&
    !code.includes("uv run")
  ) {
    issues.push({
      type: "missing-import",
      message: "References hephaestus but no import statement found",
      severity: "info",
    });
  }

  // Check for outdated patterns
  if (code.includes("mkdocs")) {
    issues.push({
      type: "outdated-reference",
      message: "References mkdocs (migration to Starlight complete)",
      severity: "warning",
    });
  }

  return issues;
}

function validateBashSyntax(code) {
  const issues = [];

  // Check for common Bash issues
  if (code.includes("cd ") && code.split("\n").length === 1) {
    issues.push({
      type: "incomplete-command",
      message: "cd command without subsequent commands",
      severity: "info",
    });
  }

  return issues;
}

function validateCodeBlock(block) {
  const { language, code } = block;

  switch (language.toLowerCase()) {
    case "python":
    case "py":
      return validatePythonSyntax(code);
    case "bash":
    case "sh":
    case "shell":
      return validateBashSyntax(code);
    default:
      return [];
  }
}

function main() {
  console.log("🔍 Validating code examples...\n");

  const files = getAllMarkdownFiles(DOCS_DIR);
  const allIssues = [];
  let totalBlocks = 0;

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    const blocks = extractCodeBlocks(content, file);
    totalBlocks += blocks.length;

    for (const block of blocks) {
      const issues = validateCodeBlock(block);

      if (issues.length > 0) {
        allIssues.push({
          file: file.replace(DOCS_DIR, ""),
          block,
          issues,
        });
      }
    }
  }

  console.log(
    `📊 Scanned ${totalBlocks} code blocks in ${files.length} files\n`,
  );

  if (allIssues.length === 0) {
    console.log("✅ All code examples look good!");
    process.exit(0);
  }

  console.log(`⚠️  Found ${allIssues.length} potential issues:\n`);

  for (const { file, block, issues } of allIssues) {
    console.log(`  📄 ${file} (${block.language})`);
    for (const issue of issues) {
      const icon = issue.severity === "warning" ? "⚠️" : "ℹ️";
      console.log(`     ${icon} ${issue.message}`);
    }
    console.log();
  }

  console.log("💡 Review and update these code examples as needed.");
}

main();
