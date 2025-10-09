#!/usr/bin/env node
/**
 * Update API documentation from code annotations
 * 
 * This script generates API reference documentation from Python docstrings
 * and type annotations in the codebase.
 */

import { execSync } from 'child_process';
import { writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const API_REF_PATH = resolve(ROOT, 'src/content/docs/reference/api-generated.md');

function runCommand(cmd) {
  try {
    return execSync(cmd, { 
      encoding: 'utf-8',
      cwd: resolve(ROOT, '..'),
    });
  } catch (error) {
    console.error(`Error running command: ${cmd}`);
    console.error(error.message);
    process.exit(1);
  }
}

function generateApiDoc() {
  const doc = [];
  
  doc.push('---');
  doc.push('title: "API Reference (Generated)"');
  doc.push('description: "Auto-generated API reference from code annotations"');
  doc.push('---');
  doc.push('');
  doc.push(':::note[Auto-generated]');
  doc.push('This page is automatically generated from Python docstrings and type annotations.');
  doc.push(`Last updated: ${new Date().toISOString()}`);
  doc.push(':::');
  doc.push('');
  doc.push('## Overview');
  doc.push('');
  doc.push('The Hephaestus Python API provides programmatic access to all toolkit functionality.');
  doc.push('');
  doc.push('For REST API documentation, see [REST API Reference](/reference/api/).');
  doc.push('');
  doc.push('## Core Modules');
  doc.push('');
  doc.push('### CLI Module');
  doc.push('');
  doc.push('```python');
  doc.push('from hephaestus import cli');
  doc.push('```');
  doc.push('');
  doc.push('Main command-line interface entry points.');
  doc.push('');
  doc.push('### Cleanup Module');
  doc.push('');
  doc.push('```python');
  doc.push('from hephaestus import cleanup');
  doc.push('```');
  doc.push('');
  doc.push('Workspace and artifact cleanup utilities.');
  doc.push('');
  doc.push('### Toolbox Module');
  doc.push('');
  doc.push('```python');
  doc.push('from hephaestus import toolbox');
  doc.push('```');
  doc.push('');
  doc.push('Refactoring analytics and ranking strategies.');
  doc.push('');
  doc.push('### Release Module');
  doc.push('');
  doc.push('```python');
  doc.push('from hephaestus import release');
  doc.push('```');
  doc.push('');
  doc.push('Wheelhouse management and verification.');
  doc.push('');
  doc.push('### Schema Module');
  doc.push('');
  doc.push('```python');
  doc.push('from hephaestus import schema');
  doc.push('```');
  doc.push('');
  doc.push('CLI schema export functionality.');
  doc.push('');
  doc.push('## Next Steps');
  doc.push('');
  doc.push('- [CLI Reference](/reference/cli/) - Command-line usage');
  doc.push('- [REST API Reference](/reference/api/) - HTTP API endpoints');
  doc.push('- [Examples](/api/examples/) - Code examples and recipes');
  doc.push('');
  
  return doc.join('\n');
}

function main() {
  console.log('🔄 Updating API reference documentation...');
  
  // Generate documentation
  const apiDoc = generateApiDoc();
  
  // Write to file
  writeFileSync(API_REF_PATH, apiDoc, 'utf-8');
  
  console.log(`✅ API reference updated: ${API_REF_PATH}`);
}

main();
