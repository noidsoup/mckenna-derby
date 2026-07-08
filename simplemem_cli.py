#!/usr/bin/env python3
"""
SimpleMem CLI - Command-line interface for SimpleMem memory operations.

Usage:
    python simplemem_cli.py add --text "Memory content" --metadata key=value
    python simplemem_cli.py query --question "What did we do?"
    python simplemem_cli.py import-ai-session --path AI_SESSION_MEMORY.md
    python simplemem_cli.py import-docs --dir docs
    python simplemem_cli.py sync          # re-import everything
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any

from simplemem_client import SimpleMemClient, load_simplemem_settings


def parse_metadata(metadata_args: list) -> Dict[str, Any]:
    """Parse metadata from key=value pairs."""
    metadata = {}
    for arg in metadata_args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def import_ai_session(file_path: str, client: SimpleMemClient) -> None:
    """Import AI session memory from markdown file.

    Handles two header styles:
      - ## Session: <title>
      - ## <title> (<date>)
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        return

    content = path.read_text()

    # Match any ## heading and the body that follows it
    section_pattern = r"^## (.+?)\n(.*?)(?=\n## |\Z)"
    sections = re.findall(section_pattern, content, re.DOTALL | re.MULTILINE)

    if not sections:
        print(f"No sections found in {file_path}")
        return

    print(f"Found {len(sections)} sections to import...", flush=True)

    imported = 0
    for i, (title, body) in enumerate(sections, 1):
        title = title.strip()
        body = body.strip()
        if not body:
            print(f"  - Skipped section {i}: {title[:50]} (empty body)")
            continue

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        if not date_match:
            date_match = re.search(r"\((\w+ \d{1,2},? \d{4})\)", title)
        date = date_match.group(1) if date_match else "Unknown date"

        lines = body.split("\n")
        summary = "\n".join(lines[:15])
        text = f"AI Session: {title}\n\n{summary}"
        metadata = {
            "source": "ai_session_memory",
            "date": date,
            "session_title": title,
            "session_number": i,
        }

        try:
            client.add_memory(text, metadata)
            imported += 1
            print(f"  ✓ Imported section {i}: {title[:60]}...", flush=True)
        except Exception as e:
            print(f"  ✗ Failed to import section {i}: {e}")

    print(f"\nImported {imported}/{len(sections)} sections to SimpleMem")


def import_docs(docs_dir: str, client: SimpleMemClient) -> None:
    """Import all markdown files from a docs directory."""
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"Error: Directory not found: {docs_dir}")
        return

    md_files = sorted(docs_path.rglob("*.md"))
    if not md_files:
        print(f"No .md files found in {docs_dir}")
        return

    print(f"Found {len(md_files)} doc files to import...", flush=True)
    imported = 0
    for i, f in enumerate(md_files, 1):
        content = f.read_text().strip()
        if not content:
            continue
        lines = content.split("\n")
        title = lines[0].lstrip("#").strip() if lines[0].startswith("#") else f.stem.replace("-", " ").title()
        summary = "\n".join(lines[:20])
        text = f"Doc: {title} ({f})\n\n{summary}"
        metadata = {"source": "docs", "file": str(f), "title": title}
        try:
            client.add_memory(text, metadata)
            imported += 1
            if i % 10 == 0 or i == len(md_files):
                print(f"  ✓ {i}/{len(md_files)} imported...", flush=True)
        except Exception as e:
            print(f"  ✗ Failed {f}: {e}", flush=True)
    print(f"\nDone: imported {imported}/{len(md_files)} docs", flush=True)


def sync_all(client: SimpleMemClient) -> None:
    """Clear local store and re-import all sources (session memory, runbook, docs)."""
    # Clear local store
    local_path = Path(client.settings.local_dir) / "memories.json"
    if local_path.exists():
        local_path.write_text(json.dumps([]))
        print("✓ Cleared local memory store", flush=True)

    sources = [
        ("AI_SESSION_MEMORY.md", "ai_session_memory"),
        ("AI_RUNBOOK.md", "ai_runbook"),
    ]
    for filepath, _source in sources:
        if Path(filepath).exists():
            print(f"\n── Importing {filepath} ──", flush=True)
            import_ai_session(filepath, client)
        else:
            print(f"  - Skipped {filepath} (not found)")

    if Path("docs").exists():
        print("\n── Importing docs/ ──", flush=True)
        import_docs("docs", client)

    # Count results
    if local_path.exists():
        memories = json.loads(local_path.read_text())
        print(f"\n✓ Sync complete: {len(memories)} total memories in local store", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="SimpleMem CLI - Manage project memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="cmd", help="Commands")

    # add
    add_parser = subparsers.add_parser("add", help="Add a memory entry")
    add_parser.add_argument("--text", required=True, help="Memory text")
    add_parser.add_argument("--metadata", nargs="*", default=[], help="key=value pairs")

    # query
    query_parser = subparsers.add_parser("query", help="Query memories")
    query_parser.add_argument("--question", required=True, help="Question to search for")
    query_parser.add_argument("--format", choices=["text", "json"], default="text")

    # import-ai-session
    import_parser = subparsers.add_parser("import-ai-session", help="Import AI session memory")
    import_parser.add_argument("--path", required=True, help="Path to AI_SESSION_MEMORY.md")

    # import-docs
    import_docs_parser = subparsers.add_parser("import-docs", help="Import markdown files from a directory")
    import_docs_parser.add_argument("--dir", default="docs", help="Path to docs directory (default: docs)")

    # sync
    subparsers.add_parser("sync", help="Clear local store and re-import everything")

    args = parser.parse_args()
    settings = load_simplemem_settings()
    client = SimpleMemClient(settings)

    if not settings.enabled:
        print("Warning: SimpleMem is disabled (SIMPLEMEM_ENABLED=false)")
        print("Set SIMPLEMEM_ENABLED=true in .env to enable")
        return

    if args.cmd == "add":
        metadata = parse_metadata(args.metadata)
        try:
            client.add_memory(args.text, metadata)
            print("✓ Memory added successfully")
        except Exception as e:
            print(f"✗ Failed to add memory: {e}")

    elif args.cmd == "query":
        try:
            result = client.query(args.question)
            if args.format == "json":
                print(result)
            else:
                data = json.loads(result)
                if "results" in data:
                    results = data["results"]
                    print(f"Found {len(results)} results:\n")
                    for i, item in enumerate(results, 1):
                        if isinstance(item, dict):
                            content = item.get("content", item.get("text", str(item)))
                            print(f"{i}. {content[:200]}...")
                        else:
                            print(f"{i}. {str(item)[:200]}...")
                else:
                    print(result)
        except Exception as e:
            print(f"✗ Query failed: {e}")

    elif args.cmd == "import-ai-session":
        import_ai_session(args.path, client)

    elif args.cmd == "import-docs":
        import_docs(args.dir, client)

    elif args.cmd == "sync":
        sync_all(client)


if __name__ == "__main__":
    main()
