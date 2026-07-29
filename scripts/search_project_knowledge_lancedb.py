#!/usr/bin/env python3
"""
Semantic search over the local LanceDB project knowledge index.

Requires a prior ``index_project_knowledge_lancedb.py --apply`` run.

Example::

    python3 -u scripts/search_project_knowledge_lancedb.py "void commission invoice" --top-k 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from project_knowledge_lancedb_common import (  # noqa: E402
    DEFAULT_MODEL,
    TABLE_NAME,
    db_has_table,
    default_index_dir,
    read_meta,
    repo_root,
)


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
    ap.add_argument("query", help="Natural language query.")
    ap.add_argument("--top-k", type=int, default=8, dest="top_k")
    ap.add_argument(
        "--json",
        action="store_true",
        help="Print results as JSON (source_path, chunk_index, _distance, text preview).",
    )
    args = ap.parse_args()
    if args.top_k < 1:
        print("--top-k must be >= 1", flush=True)
        return 2

    root = repo_root()
    index_dir = default_index_dir(root)
    meta = read_meta(index_dir)
    if not meta:
        print(f"No index meta at {index_dir}. Run index_project_knowledge_lancedb.py --apply first.", flush=True)
        return 1

    import lancedb

    db = lancedb.connect(str(index_dir))
    if not db_has_table(db, TABLE_NAME):
        print(f"Table {TABLE_NAME!r} missing under {index_dir}. Re-run indexer with --apply.", flush=True)
        return 1

    model_name = meta.get("embedding_model", DEFAULT_MODEL)
    from sentence_transformers import SentenceTransformer

    print(f"Loading {model_name} …", flush=True)
    model = SentenceTransformer(model_name)
    qvec = model.encode(
        [args.query],
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]
    q = np.asarray(qvec, dtype=np.float32)

    table = db.open_table(TABLE_NAME)
    res = (
        table.search(q.tolist())
        .select(["chunk_id", "source_path", "chunk_index", "text", "_distance"])
        .limit(args.top_k)
        .to_list()
    )

    if args.json:
        out = []
        for row in res:
            txt = row.get("text") or ""
            out.append(
                {
                    "source_path": row.get("source_path"),
                    "chunk_index": row.get("chunk_index"),
                    "_distance": row.get("_distance"),
                    "text_preview": txt[:500],
                }
            )
        print(json.dumps(out, indent=2), flush=True)
        return 0

    print(f"Top {len(res)} hits (lower _distance is closer for L2 on normalized vectors):\n", flush=True)
    for i, row in enumerate(res, 1):
        sp = row.get("source_path")
        dist = row.get("_distance")
        txt = (row.get("text") or "").replace("\n", " ")[:320]
        print(f"--- {i}. {sp}  (_distance={dist:.4f})", flush=True)
        print(f"{txt}", flush=True)
        print("", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
