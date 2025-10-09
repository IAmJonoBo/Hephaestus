#!/usr/bin/env node
/**
 * Update CLI reference documentation from Typer schemas
 * 
 * This script:
 * 1. Runs `hephaestus schema --output` to get CLI schemas
 * 2. Parses the JSON output
 * 3. Generates markdown documentation
 * 4. Updates the CLI reference page
 */

import { execSync } from 'child_process';
import { writeFileSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const CLI_REF_PATH = resolve(ROOT, 'src/content/docs/reference/cli.md');

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

function generateCliDoc(schemas) {
  const doc = [];
  
  doc.push('---');
  doc.push('title: "CLI Reference"');
  doc.push('description: "Complete command-line interface reference for Hephaestus toolkit"');
  doc.push('---');
  doc.push('');
  doc.push(':::note[Auto-generated]');
  doc.push('This page is automatically generated from the CLI schemas.');
  doc.push(`Last updated: ${new Date().toISOString()}`);
  doc.push(':::');
  doc.push('');
  doc.push('## Overview');
  doc.push('');
  doc.push('The Hephaestus CLI provides commands for quality gates, refactoring analysis, and project automation.');
  doc.push('');
  doc.push('## Commands');
  doc.push('');

  // Sort commands alphabetically
  const commands = Object.keys(schemas).sort();
  
  for (const cmdName of commands) {
    const cmd = schemas[cmdName];
    
    doc.push(`### \`hephaestus ${cmdName}\``);
    doc.push('');
    
    if (cmd.description) {
      doc.push(cmd.description);
      doc.push('');
    }
    
    // Usage
    doc.push('**Usage:**');
    doc.push('');
    doc.push('```bash');
    doc.push(`hephaestus ${cmdName} ${cmd.usage || ''}`);
    doc.push('```');
    doc.push('');
    
    // Parameters
    if (cmd.parameters && cmd.parameters.length > 0) {
      doc.push('**Parameters:**');
      doc.push('');
      
      for (const param of cmd.parameters) {
        const required = param.required ? ' _(required)_' : '';
        const defaultVal = param.default ? ` Default: \`${param.default}\`` : '';
        doc.push(`- \`${param.name}\`${required}: ${param.help}${defaultVal}`);
      }
      doc.push('');
    }
    
    // Options
    if (cmd.options && cmd.options.length > 0) {
      doc.push('**Options:**');
      doc.push('');
      
      for (const opt of cmd.options) {
        const flags = opt.flags ? opt.flags.join(', ') : opt.name;
        const defaultVal = opt.default !== undefined ? ` Default: \`${opt.default}\`` : '';
        doc.push(`- \`${flags}\`: ${opt.help}${defaultVal}`);
      }
      doc.push('');
    }
    
    // Examples
    if (cmd.examples && cmd.examples.length > 0) {
      doc.push('**Examples:**');
      doc.push('');
      
      for (const example of cmd.examples) {
        doc.push('```bash');
        doc.push(example);
        doc.push('```');
        doc.push('');
      }
    }
    
    doc.push('---');
    doc.push('');
  }
  
  return doc.join('\n');
}

function main() {
  console.log('🔄 Updating CLI reference documentation...');
  
  // Export schemas
  const schemasJson = runCommand('uv run hephaestus schema --output /tmp/schemas.json');
  
  // Read schemas
  let schemas;
  try {
    const schemasContent = readFileSync('/tmp/schemas.json', 'utf-8');
    schemas = JSON.parse(schemasContent);
  } catch (error) {
    console.error('Error reading schemas:', error.message);
    process.exit(1);
  }
  
  // Generate documentation
  const cliDoc = generateCliDoc(schemas.commands || schemas);
  
  // Write to file
  writeFileSync(CLI_REF_PATH, cliDoc, 'utf-8');
  
  console.log(`✅ CLI reference updated: ${CLI_REF_PATH}`);
}

main();
