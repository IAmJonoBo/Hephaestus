#!/usr/bin/env python3
"""
Migrate documentation from MkDocs format to Astro Starlight format.

This script:
1. Reads all markdown files from the docs/ directory
2. Converts internal links from MkDocs to Starlight format
3. Adds proper frontmatter for Starlight
4. Preserves Diátaxis structure
5. Copies files to docs-site/src/content/docs/
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional


def extract_title_from_content(content: str) -> Optional[str]:
    """Extract title from first H1 heading in markdown content."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else None


def generate_description(content: str, max_length: int = 160) -> str:
    """Generate description from content."""
    # Remove markdown formatting
    text = re.sub(r"#.*\n", "", content)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"[`*_]", "", text)
    text = " ".join(text.split())

    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "..."
    return text


def convert_links(content: str, current_file_path: Path) -> str:
    """
    Convert MkDocs-style links to Starlight format.

    MkDocs: [text](../path/file.md) or [text](file.md)
    Starlight: [text](/path/file/)
    """

    def replace_link(match):
        text = match.group(1)
        link = match.group(2)

        # Skip external links
        if link.startswith(("http://", "https://", "#")):
            return match.group(0)

        # Skip links to non-markdown files
        if not link.endswith(".md"):
            return match.group(0)

        # Remove .md extension
        link = link.replace(".md", "")

        # Convert relative paths to absolute
        if link.startswith("../"):
            # Calculate absolute path
            parts = link.split("/")
            # Remove '..' and current directory references
            clean_parts = [p for p in parts if p and p != ".."]
            link = "/" + "/".join(clean_parts)
        elif not link.startswith("/"):
            # Relative link in same directory
            parent_dir = current_file_path.parent.name
            if parent_dir != "docs":
                link = f"/{parent_dir}/{link}"
            else:
                link = f"/{link}"

        # Ensure trailing slash
        if not link.endswith("/"):
            link += "/"

        return f"[{text}]({link})"

    return re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", replace_link, content)


def add_frontmatter(content: str, title: Optional[str], description: str) -> str:
    """Add Starlight frontmatter to content."""
    # Check if frontmatter already exists
    if content.startswith("---"):
        return content

    frontmatter_parts = ["---"]

    if title:
        # Escape quotes in title
        title = title.replace('"', '\\"')
        frontmatter_parts.append(f'title: "{title}"')

    if description:
        description = description.replace('"', '\\"')
        frontmatter_parts.append(f'description: "{description}"')

    frontmatter_parts.append("---")
    frontmatter_parts.append("")

    # Remove the first H1 heading since Starlight will generate it from title
    content_without_first_h1 = re.sub(r"^#\s+.+\n+", "", content, count=1)

    return "\n".join(frontmatter_parts) + content_without_first_h1


def migrate_file(src_path: Path, dest_base: Path, docs_base: Path) -> None:
    """Migrate a single markdown file."""
    # Read source content
    content = src_path.read_text(encoding="utf-8")

    # Extract title and generate description
    title = extract_title_from_content(content)
    description = generate_description(content)

    # Convert links
    content = convert_links(content, src_path)

    # Add frontmatter
    content = add_frontmatter(content, title, description)

    # Calculate destination path
    rel_path = src_path.relative_to(docs_base)
    dest_path = dest_base / rel_path

    # Create parent directories
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Write destination file
    dest_path.write_text(content, encoding="utf-8")
    print(f"✓ Migrated: {rel_path}")


def migrate_all_docs(docs_dir: Path, dest_dir: Path) -> None:
    """Migrate all documentation files."""
    print(f"Migrating documentation from {docs_dir} to {dest_dir}")
    print()

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Find all markdown files
    md_files = list(docs_dir.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files to migrate")
    print()

    # Migrate each file
    for md_file in md_files:
        try:
            migrate_file(md_file, dest_dir, docs_dir)
        except Exception as e:
            print(f"✗ Error migrating {md_file}: {e}")

    print()
    print(f"Migration complete! {len(md_files)} files processed.")


def create_index_redirects(dest_dir: Path) -> None:
    """Create index.md files that redirect to main content."""
    # Common directories that need index pages
    directories = [
        "tutorials",
        "how-to",
        "explanation",
        "reference",
        "adr",
    ]

    index_contents = {
        "tutorials": {
            "title": "Tutorials",
            "description": "Step-by-step tutorials to get started with Hephaestus",
            "content": "Learn how to use Hephaestus through hands-on tutorials.",
        },
        "how-to": {
            "title": "How-To Guides",
            "description": "Practical guides for common tasks and workflows",
            "content": "Task-oriented guides for accomplishing specific goals with Hephaestus.",
        },
        "explanation": {
            "title": "Explanation",
            "description": "Understanding the concepts and architecture behind Hephaestus",
            "content": "Deep-dive explanations of Hephaestus concepts, architecture, and design decisions.",
        },
        "reference": {
            "title": "Reference",
            "description": "Technical reference documentation",
            "content": "Complete technical reference for all Hephaestus APIs, CLI commands, and configurations.",
        },
        "adr": {
            "title": "Architecture Decision Records",
            "description": "Document important architectural decisions",
            "content": "Architecture Decision Records (ADRs) documenting key technical decisions in the project.",
        },
    }

    for dir_name in directories:
        dir_path = dest_dir / dir_name
        if dir_path.exists() and not (dir_path / "index.md").exists():
            info = index_contents.get(
                dir_name,
                {
                    "title": dir_name.replace("-", " ").title(),
                    "description": f"{dir_name} documentation",
                    "content": f"Documentation for {dir_name}.",
                },
            )

            index_content = f"""---
title: "{info["title"]}"
description: "{info["description"]}"
---

# {info["title"]}

{info["content"]}
"""
            index_path = dir_path / "index.md"
            index_path.write_text(index_content, encoding="utf-8")
            print(f"✓ Created index: {dir_name}/index.md")


def main():
    """Main migration function."""
    # Get repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    docs_dir = repo_root / "docs"
    dest_dir = repo_root / "docs-site" / "src" / "content" / "docs"

    if not docs_dir.exists():
        print(f"Error: Source docs directory not found: {docs_dir}")
        return 1

    # Run migration
    migrate_all_docs(docs_dir, dest_dir)

    # Create index files
    print()
    print("Creating index pages...")
    create_index_redirects(dest_dir)

    print()
    print("✨ Migration complete!")
    print()
    print("Next steps:")
    print("1. cd docs-site")
    print("2. npm install")
    print("3. npm run dev")
    print("4. Review the migrated content at http://localhost:4321")

    return 0


if __name__ == "__main__":
    exit(main())
