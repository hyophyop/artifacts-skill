#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=os.fspath(cwd) if cwd else None, check=True)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Bootstrap a repo-local Python environment under .artifacts/.venv for the artifacts skill."
    )
    p.add_argument("--repo-root", default="", help="Repo root override (default: infer by walking up to .git).")
    p.add_argument("--python", default=sys.executable, help="Python to use for creating the venv.")
    p.add_argument(
        "--recreate",
        action="store_true",
        help="If set, delete existing .artifacts/.venv before creating a fresh one.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _find_repo_root(Path.cwd())
    state_root = repo_root / ".artifacts"
    venv_dir = state_root / ".venv"
    state_root.mkdir(parents=True, exist_ok=True)

    if args.recreate and venv_dir.exists():
        # Only ever delete inside .artifacts to satisfy "all byproducts live under .artifacts".
        import shutil

        shutil.rmtree(venv_dir)

    if not venv_dir.exists():
        _run([str(args.python), "-m", "venv", os.fspath(venv_dir)])

    py = venv_dir / "bin" / "python"
    pip = [os.fspath(py), "-m", "pip"]
    _run(pip + ["install", "--upgrade", "pip"])
    _run(pip + ["install", "chromadb"])

    manifest: dict[str, Any] = {
        "created_at": _now_utc_iso(),
        "repo_root": os.fspath(repo_root),
        "venv": os.fspath(venv_dir),
        "python": os.fspath(py),
        "installed": ["chromadb"],
        "version": 1,
    }
    (state_root / "env_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

