#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    repo_root: Path
    artifacts_root: Path


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_request_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{stamp}_{suffix}"


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _paths(cwd: Path) -> Paths:
    repo_root = _find_repo_root(cwd)
    return Paths(repo_root=repo_root, artifacts_root=repo_root / ".artifacts" / "artifacts")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Initialize a .artifacts/artifacts/{request_id} workspace.")
    p.add_argument("--request-id", default="", help="Override request id (default: timestamp_uuid).")
    p.add_argument("--request", required=True, help="The user request text to capture.")
    p.add_argument(
        "--repo-root",
        default="",
        help="Repo root override (default: infer by walking up to .git from CWD).",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    cwd = Path.cwd()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _find_repo_root(cwd)
    paths = _paths(repo_root)

    request_id = str(args.request_id).strip() or _default_request_id()
    run_dir = paths.artifacts_root / request_id
    run_dir.mkdir(parents=True, exist_ok=False)

    created_at = _now_utc_iso()
    manifest = {
        "request_id": request_id,
        "created_at": created_at,
        "updated_at": created_at,
        "status": "pending_confirmation",
        "request": str(args.request).strip(),
        "cwd": os.fspath(cwd),
        "repo_root": os.fspath(paths.repo_root),
        "version": 1,
    }

    manifest_path = run_dir / "manifest.json"
    _write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    plan_path = run_dir / "plan.md"
    todo_path = run_dir / "todo.md"
    walkthrough_path = run_dir / "walkthrough.md"

    _write_text(
        plan_path,
        "\n".join(
            [
                f"# Plan ({request_id})",
                "",
                "## Request",
                str(args.request).strip(),
                "",
                "## Context",
                "- Goal:",
                "- Success criteria:",
                "- Scope (in / out):",
                "- Constraints / dependencies:",
                "",
                "## Assumptions / Open Questions",
                "- [ ] ",
                "",
                "## Planned Steps",
                "1) Discovery / review (files, logs, configs)",
                "2) Design / approach (what + why)",
                "3) Implementation (specific files/areas)",
                "4) Validation (tests/checks/inspections)",
                "5) Documentation (walkthrough + TODO checks)",
                "",
                "## Risks / Rollback",
                "- Risk:",
                "- Mitigation:",
                "- Rollback plan:",
                "",
                "## Artifacts to Produce",
                "- `todo.md` 체크 완료",
                "- `walkthrough.md` 상세 기록",
                "",
                "## Confirmation",
                "Reply `진행해줘` to confirm execution.",
                "",
            ]
        ),
    )
    _write_text(
        todo_path,
        "\n".join(
            [
                f"# TODO ({request_id})",
                "",
                "## Intake",
                "- [ ] User confirmed execution",
                "- [ ] Scope locked (plan matches request)",
                "",
                "## Execution",
                "- [ ] Changes implemented",
                "- [ ] Edge cases handled",
                "- [ ] No unrelated files modified",
                "",
                "## Validation",
                "- [ ] Tests / checks executed (or explicitly skipped with reason)",
                "- [ ] Results recorded in walkthrough",
                "",
                "## Documentation",
                "- [ ] Walkthrough includes plan, steps, commands, and outcomes",
                "- [ ] Files changed listed with paths",
                "",
                "## Indexing",
                "- [ ] Indexed into ChromaDB (.artifacts/)",
                "",
            ]
        ),
    )
    _write_text(
        walkthrough_path,
        "\n".join(
            [
                f"# Walkthrough ({request_id})",
                "",
                "## Summary (1-3 bullets)",
                "- What was requested",
                "- What was done",
                "- Final status",
                "",
                "## Plan Snapshot",
                "- Goals:",
                "- Assumptions:",
                "- Scope decisions:",
                "",
                "## Work Log (chronological)",
                "1) ",
                "2) ",
                "3) ",
                "",
                "## Decisions / Tradeoffs",
                "- Decision:",
                "- Rationale:",
                "",
                "## Files Changed",
                "- `path/to/file` (what/why)",
                "",
                "## Commands / Checks",
                "- `command` (result)",
                "",
                "## Validation Results",
                "- Tests/checks:",
                "- Outcomes:",
                "",
                "## Follow-ups / Notes",
                "- ",
                "",
            ]
        ),
    )

    out = {
        "request_id": request_id,
        "run_dir": os.fspath(run_dir),
        "plan": os.fspath(plan_path),
        "todo": os.fspath(todo_path),
        "walkthrough": os.fspath(walkthrough_path),
        "manifest": os.fspath(manifest_path),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
