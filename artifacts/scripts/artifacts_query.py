#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query artifacts ChromaDB index in .artifacts/chroma_db.")
    p.add_argument("query", help="Query string.")
    p.add_argument("--repo-root", default="", help="Repo root override (default: infer by walking up to .git).")
    p.add_argument("--n", type=int, default=5, help="Number of results.")
    return p.parse_args()


def _get_collection(chroma_root: Path):
    if chromadb is None:
        raise SystemExit(
            "chromadb is not available in this Python environment.\n"
            "Fix: run with a Python environment located under `.artifacts/` "
            "(e.g. `.artifacts/.venv`) and install chromadb there."
        )
    client = chromadb.PersistentClient(path=os.fspath(chroma_root))
    return client.get_or_create_collection(name="artifacts", metadata={"hnsw:space": "cosine"})

def _ensure_artifacts_venv(repo_root: Path) -> None:
    exe = Path(sys.executable).resolve()
    artifacts_root = (repo_root / ".artifacts").resolve()
    try:
        exe.relative_to(artifacts_root)
    except Exception:
        raise SystemExit(
            "This command must be run using a Python interpreter located under `.artifacts/`.\n"
            f"Detected sys.executable: {exe}\n\n"
            "Fix:\n"
            "- Create env: `python3 \"$CODEX_HOME/skills/artifacts/scripts/artifacts_bootstrap_env.py\"`\n"
            "- Re-run with: `.artifacts/.venv/bin/python \"$CODEX_HOME/skills/artifacts/scripts/artifacts_query.py\" \"<query>\"`"
        )


def main() -> None:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _find_repo_root(Path.cwd())
    _ensure_artifacts_venv(repo_root)
    chroma_root = repo_root / ".artifacts" / "chroma_db"
    collection = _get_collection(chroma_root)

    results = collection.query(query_texts=[args.query], n_results=int(args.n))
    out: list[dict[str, Any]] = []
    if results and results.get("ids"):
        ids = results["ids"][0] or []
        metas = results.get("metadatas", [[]])[0] or []
        dists = results.get("distances", [[]])[0] or []
        for i, rid in enumerate(ids):
            item = dict(metas[i] or {})
            item["id"] = rid
            if i < len(dists):
                item["distance"] = dists[i]
            out.append(item)

    print(json.dumps({"query": args.query, "results": out, "chroma_root": os.fspath(chroma_root)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
