#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None


DEFAULT_TTL_DAYS = 7


@dataclass(frozen=True)
class Layout:
    repo_root: Path
    artifacts_root: Path
    state_root: Path
    chroma_root: Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _layout(repo_root: Path | None) -> Layout:
    root = repo_root.resolve() if repo_root else _find_repo_root(Path.cwd())
    state_root = root / ".artifacts"
    return Layout(
        repo_root=root,
        artifacts_root=state_root / "artifacts",
        state_root=state_root,
        chroma_root=state_root / "chroma_db",
    )


def _parse_dt(value: str) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_runs(artifacts_root: Path) -> list[Path]:
    if not artifacts_root.exists():
        return []
    return [p for p in sorted(artifacts_root.iterdir()) if p.is_dir()]


def _prune_old(*, runs: list[Path], ttl_days: int) -> tuple[list[str], list[Path]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    deleted_ids: list[str] = []
    kept: list[Path] = []
    for run_dir in runs:
        manifest = _read_json(run_dir / "manifest.json") or {}
        req_id = str(manifest.get("request_id") or run_dir.name).strip()
        created_at = _parse_dt(str(manifest.get("created_at") or "")) or None
        if created_at is not None and created_at < cutoff:
            try:
                shutil.rmtree(run_dir)
                deleted_ids.append(req_id)
                continue
            except Exception:
                # If deletion fails, keep it (do not lose data silently).
                pass
        kept.append(run_dir)
    return deleted_ids, kept


def _ensure_chroma() -> None:
    if chromadb is None:
        raise SystemExit(
            "chromadb is not available in this Python environment.\n"
            "Fix: run with a Python environment located under `.artifacts/` "
            "(e.g. `.artifacts/.venv`) and install chromadb there."
        )


def _ensure_artifacts_venv(repo_root: Path) -> None:
    """
    Enforce policy: chroma-dependent operations must run from a Python env under `.artifacts/`.
    """
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
            "- Re-run with: `.artifacts/.venv/bin/python \"$CODEX_HOME/skills/artifacts/scripts/artifacts_index.py\"`"
        )


def _get_collection(chroma_root: Path):
    _ensure_chroma()
    chroma_root.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=os.fspath(chroma_root))
    return client.get_or_create_collection(name="artifacts", metadata={"hnsw:space": "cosine"})


def _build_doc(*, run_dir: Path, manifest: dict[str, Any], repo_root: Path) -> tuple[str, dict[str, Any]]:
    req_id = str(manifest.get("request_id") or run_dir.name).strip()
    created_at = str(manifest.get("created_at") or "").strip()
    status = str(manifest.get("status") or "").strip()
    request = str(manifest.get("request") or "").strip()

    plan = _read_text(run_dir / "plan.md").strip()
    todo = _read_text(run_dir / "todo.md").strip()
    walkthrough = _read_text(run_dir / "walkthrough.md").strip()

    header = "\n".join(
        [
            f"Request ID: {req_id}",
            f"Created At: {created_at}",
            f"Status: {status}",
            "",
            "Request:",
            request,
        ]
    ).strip()
    doc = "\n\n".join([header, plan, todo, walkthrough]).strip()

    try:
        rel_run_dir = os.path.relpath(os.fspath(run_dir), start=os.fspath(repo_root))
    except Exception:
        rel_run_dir = run_dir.name

    meta = {
        "request_id": req_id,
        "created_at": created_at,
        "status": status,
        "run_dir": rel_run_dir,
        "plan_path": os.path.join(rel_run_dir, "plan.md"),
        "todo_path": os.path.join(rel_run_dir, "todo.md"),
        "walkthrough_path": os.path.join(rel_run_dir, "walkthrough.md"),
    }
    return doc, meta


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Index .artifacts/artifacts/* into ChromaDB (.artifacts/chroma_db) with TTL pruning."
    )
    p.add_argument("--repo-root", default="", help="Repo root override (default: infer by walking up to .git).")
    p.add_argument("--ttl-days", type=int, default=int(os.getenv("ARTIFACTS_TTL_DAYS", DEFAULT_TTL_DAYS)))
    p.add_argument("--request-id", default="", help="If set, index only this request id folder.")
    p.add_argument("--dry-run", action="store_true", help="Compute actions but do not write to ChromaDB or delete.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    layout = _layout(Path(args.repo_root) if args.repo_root else None)
    _ensure_artifacts_venv(layout.repo_root)
    runs = _collect_runs(layout.artifacts_root)

    if args.request_id:
        runs = [p for p in runs if p.name == args.request_id]

    deleted_ids, kept = _prune_old(runs=runs, ttl_days=int(args.ttl_days))

    if args.dry_run:
        print(
            json.dumps(
                {
                    "repo_root": os.fspath(layout.repo_root),
                    "artifacts_root": os.fspath(layout.artifacts_root),
                    "state_root": os.fspath(layout.state_root),
                    "chroma_root": os.fspath(layout.chroma_root),
                    "ttl_days": int(args.ttl_days),
                    "deleted_ids": deleted_ids,
                    "kept_runs": [p.name for p in kept],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    collection = _get_collection(layout.chroma_root)

    if deleted_ids:
        try:
            collection.delete(ids=deleted_ids)
        except Exception:
            pass

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    for run_dir in kept:
        manifest = _read_json(run_dir / "manifest.json") or {}
        req_id = str(manifest.get("request_id") or run_dir.name).strip()
        doc, meta = _build_doc(run_dir=run_dir, manifest=manifest, repo_root=layout.repo_root)
        if not doc:
            continue
        ids.append(req_id)
        docs.append(doc)
        metas.append(meta)

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)

    print(
        json.dumps(
            {"indexed": len(ids), "deleted": len(deleted_ids), "ttl_days": int(args.ttl_days), "chroma_root": os.fspath(layout.chroma_root)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
