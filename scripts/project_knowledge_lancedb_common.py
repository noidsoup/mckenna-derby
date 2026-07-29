"""
Shared helpers for local LanceDB + sentence-transformers project knowledge index.

Index directory default: ``<repo>/uncommitted/lancedb_project_knowledge`` (gitignored).
Override with env ``PROJECT_KNOWLEDGE_LANCEDB_DIR`` (absolute path recommended; ``~`` expanded).
Optional extra scan roots: ``PROJECT_KNOWLEDGE_LANCEDB_EXTRA_DIRS`` (comma-separated, repo-relative).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

TABLE_NAME = "knowledge_chunks"
META_FILE = "index_meta.json"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_index_dir(root: Path | None = None) -> Path:
    root = root or repo_root()
    env = os.environ.get("PROJECT_KNOWLEDGE_LANCEDB_DIR")
    if env:
        return Path(env).expanduser()
    return root / "uncommitted" / "lancedb_project_knowledge"


def _extra_dirs(root: Path) -> list[Path]:
    raw = os.environ.get("PROJECT_KNOWLEDGE_LANCEDB_EXTRA_DIRS", "")
    out: list[Path] = []
    resolved_root = root.resolve()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        p = (resolved_root / part).resolve()
        if p != resolved_root and resolved_root not in p.parents:
            continue
        if p.is_dir():
            out.append(p)
    return out


def discover_indexable_files(root: Path) -> list[Path]:
    """Markdown and Cursor rules under common agent/doc locations."""
    found: list[Path] = []
    singles = (
        "AGENTS.md",
        "README.md",
        "AI_RUNBOOK.md",
        "AI_SESSION_MEMORY.md",
        "MEMORY.md",
    )
    for name in singles:
        p = root / name
        if p.is_file():
            found.append(p.resolve())
    for sub in ("docs", "wiki"):
        d = root / sub
        if d.is_dir():
            found.extend(sorted(p.resolve() for p in d.rglob("*.md") if p.is_file()))
    agents = root / ".agents"
    if agents.is_dir():
        for ext in ("*.md", "*.mdc"):
            found.extend(sorted(p.resolve() for p in agents.rglob(ext) if p.is_file()))
    rules = root / ".cursor" / "rules"
    if rules.is_dir():
        found.extend(sorted(p.resolve() for p in rules.glob("*.mdc") if p.is_file()))
    for extra in _extra_dirs(root):
        found.extend(sorted(p.resolve() for p in extra.rglob("*.md") if p.is_file()))
        found.extend(sorted(p.resolve() for p in extra.rglob("*.mdc") if p.is_file()))
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def rel_posix(path: Path, root: Path) -> str:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        digest = hashlib.sha1(str(resolved_path).encode("utf-8")).hexdigest()
        return f"__external__/{resolved_path.name}-{digest}"


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    text = text.strip().replace("\r\n", "\n")
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_chars, n)
        piece = text[i:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        nxt = end - overlap
        i = nxt if nxt > i else i + 1
    return chunks


def chunk_id(source_rel: str, chunk_index: int) -> str:
    h = hashlib.sha1(f"{source_rel}#{chunk_index}".encode("utf-8")).hexdigest()
    return h


def sql_string_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def delete_paths_predicate(rel_paths: list[str]) -> str:
    parts = ", ".join(sql_string_literal(p) for p in sorted(rel_paths))
    return f"source_path IN ({parts})"


def write_meta(index_dir: Path, model_name: str, dim: int) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "embedding_model": model_name,
        "embedding_dim": dim,
        "normalize_embeddings": True,
        "table": TABLE_NAME,
    }
    (index_dir / META_FILE).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def read_meta(index_dir: Path) -> dict | None:
    p = index_dir / META_FILE
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def db_table_names(db) -> list[str]:
    names: list[str] = []
    token = None
    while True:
        resp = db.list_tables(page_token=token) if token else db.list_tables()
        names.extend(list(getattr(resp, "tables", []) or []))
        token = getattr(resp, "page_token", None) or None
        if not token:
            break
    return names


def db_has_table(db, name: str) -> bool:
    return name in db_table_names(db)
