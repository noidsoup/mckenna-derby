#!/usr/bin/env python3
"""
Build a local LanceDB index of repo markdown / rules for semantic search.

Uses ``sentence-transformers`` (default: all-MiniLM-L6-v2) — runs fully offline after
the model is cached. No Pinecone / cloud vector DB.

Dry-run by default (no model load). Use ``--apply`` to write the index under
``uncommitted/lancedb_project_knowledge/`` unless ``PROJECT_KNOWLEDGE_LANCEDB_DIR`` is set
(in shell or ``.env``; see ``.env.example``).

Examples::

    python3 -u scripts/index_project_knowledge_lancedb.py
    python3 -u scripts/index_project_knowledge_lancedb.py --apply
    python3 -u scripts/index_project_knowledge_lancedb.py --apply --files AGENTS.md docs/MOVE-CONFIRMATION-FLOW.md
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from project_knowledge_lancedb_common import (  # noqa: E402
    DEFAULT_MODEL,
    EMBED_DIM,
    META_FILE,
    TABLE_NAME,
    chunk_id,
    chunk_text,
    db_has_table,
    default_index_dir,
    delete_paths_predicate,
    discover_indexable_files,
    read_meta,
    rel_posix,
    repo_root,
    write_meta,
)


def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    print(f"Loading embedding model: {model_name} …", flush=True)
    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    elapsed = time.perf_counter() - t0
    print(f"Model ready in {elapsed:.1f}s", flush=True)
    return model


def _encode_batches(model, texts: list[str], batch_size: int) -> np.ndarray:
    """Return float32 array shape (N, dim)."""
    out: list[np.ndarray] = []
    total = len(texts)
    for start in range(0, total, batch_size):
        batch = texts[start : start + batch_size]
        vecs = model.encode(
            batch,
            batch_size=min(batch_size, len(batch)),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        out.append(np.asarray(vecs, dtype=np.float32))
        if start == 0 or (start + batch_size) % 500 == 0 or start + batch_size >= total:
            print(f"  embedded {min(start + batch_size, total)}/{total} chunks", flush=True)
    return np.vstack(out) if out else np.zeros((0, EMBED_DIM), dtype=np.float32)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(repo_root() / ".env", override=False)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    _load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write LanceDB tables and meta (default is dry-run summary only).",
    )
    ap.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"sentence-transformers model id (default: {DEFAULT_MODEL}).",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default 32).",
    )
    ap.add_argument(
        "--files",
        nargs="*",
        metavar="REL_PATH",
        help="Only re-index these repo-relative POSIX paths (e.g. AGENTS.md).",
    )
    args = ap.parse_args()
    if args.batch_size < 1:
        print("--batch-size must be >= 1", flush=True)
        return 2

    root = repo_root()
    index_dir = default_index_dir(root)
    files = discover_indexable_files(root)
    if args.files:
        want = {p.replace("\\", "/") for p in args.files}
        files = [p for p in files if rel_posix(p, root) in want]
        missing = want - {rel_posix(p, root) for p in files}
        if missing:
            print("WARNING: these --files paths were not found on disk:", flush=True)
            for m in sorted(missing):
                print(f"  - {m}", flush=True)

    if not files:
        print("No files to index.", flush=True)
        return 1

    rows_preview = 0
    for fp in files:
        try:
            raw = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"SKIP read error {fp}: {e}", flush=True)
            continue
        rows_preview += len(chunk_text(raw))

    print(f"Repo root: {root}", flush=True)
    if os.environ.get("PROJECT_KNOWLEDGE_LANCEDB_DIR"):
        print(f"Index dir: {index_dir} (PROJECT_KNOWLEDGE_LANCEDB_DIR)", flush=True)
    else:
        print(f"Index dir: {index_dir} (default under uncommitted/; gitignored)", flush=True)
    print(f"Files: {len(files)}  ~chunks: {rows_preview}", flush=True)
    if not args.apply:
        print("Dry-run only. Pass --apply to build the LanceDB index.", flush=True)
        return 0

    import lancedb

    model = _load_model(args.model)
    _ged = getattr(model, "get_embedding_dimension", None)
    if callable(_ged):
        dim = int(_ged())
    else:
        dim = int(model.get_sentence_embedding_dimension())
    if dim != EMBED_DIM and args.model == DEFAULT_MODEL:
        print(f"NOTE: model reports dim={dim} (expected {EMBED_DIM} for default model).", flush=True)

    all_texts: list[str] = []
    meta_rows: list[tuple[str, str, int]] = []
    for fp in files:
        rel = rel_posix(fp, root)
        try:
            raw = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"SKIP read error {rel}: {e}", flush=True)
            continue
        parts = chunk_text(raw)
        for i, text in enumerate(parts):
            all_texts.append(text)
            meta_rows.append((chunk_id(rel, i), rel, i))

    if not all_texts:
        print("No chunks produced.", flush=True)
        return 1

    print(f"Embedding {len(all_texts)} chunks …", flush=True)
    t0 = time.perf_counter()
    mat = _encode_batches(model, all_texts, args.batch_size)
    print(f"Embedding done in {time.perf_counter() - t0:.1f}s", flush=True)

    index_dir.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(index_dir))

    partial = bool(args.files)
    rel_paths = sorted({rel_posix(p, root) for p in files})

    if partial and db_has_table(db, TABLE_NAME):
        table = db.open_table(TABLE_NAME)
        pred = delete_paths_predicate(rel_paths)
        print(f"Deleting existing rows: {pred}", flush=True)
        table.delete(pred)
        records = []
        for (cid, rel, idx), text, row in zip(meta_rows, all_texts, mat):
            records.append(
                {
                    "chunk_id": cid,
                    "source_path": rel,
                    "chunk_index": int(idx),
                    "text": text,
                    "vector": row.astype(np.float32).tolist(),
                }
            )
        batch_n = 256
        for i in range(0, len(records), batch_n):
            sub = records[i : i + batch_n]
            table.add(sub)
            print(f"  appended rows {i + len(sub)}/{len(records)}", flush=True)
    else:
        if db_has_table(db, TABLE_NAME):
            print(f"Dropping existing table {TABLE_NAME!r}", flush=True)
            db.drop_table(TABLE_NAME)
        records = []
        for (cid, rel, idx), text, row in zip(meta_rows, all_texts, mat):
            records.append(
                {
                    "chunk_id": cid,
                    "source_path": rel,
                    "chunk_index": int(idx),
                    "text": text,
                    "vector": row.astype(np.float32).tolist(),
                }
            )
        batch_n = 256
        first = records[:batch_n]
        rest = records[batch_n:]
        print(f"Creating table {TABLE_NAME!r} with {len(first)} rows …", flush=True)
        table = db.create_table(TABLE_NAME, first)
        for i in range(0, len(rest), batch_n):
            sub = rest[i : i + batch_n]
            table.add(sub)
            print(f"  added rows {len(first) + i + len(sub)}/{len(records)}", flush=True)

    write_meta(index_dir, args.model, dim)
    existing = read_meta(index_dir)
    print(f"Wrote meta: {index_dir / META_FILE} -> {existing}", flush=True)
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
