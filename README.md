# artifacts (Codex skill)

This repository contains the `artifacts` skill for OpenAI Codex CLI.

The skill creates a structured, repo-local audit trail for each task request (plan → todo → walkthrough), and indexes the finished work into a repo-local ChromaDB index for 7-day recall.

## Features

- **Confirm-before-execute workflow**: generate `plan.md` + `todo.md` first, ask for confirmation, then implement.
- **Detailed artifacts**: the real plan/process/validation lives in `.artifacts/artifacts/{request_id}/`.
- **Repo-local semantic recall**: index completed work into `.artifacts/chroma_db/` and query it later.
- **Retention**: artifacts + index are pruned after 7 days (configurable).
- **Byproduct policy**: all skill byproducts are kept under `.artifacts/`.

## Install

1) Clone this repo.

2) Copy the skill into your Codex skills directory:

```bash
mkdir -p "$CODEX_HOME/skills/artifacts"
rsync -a --delete artifacts/ "$CODEX_HOME/skills/artifacts/"
```

If `CODEX_HOME` is not set, it is typically `~/.codex`.

## Quickstart (inside the target repo)

All commands below assume you are in the repository where you want the `.artifacts/` folder to live.

### 0) Bootstrap the required environment under `.artifacts/`

This creates `.artifacts/.venv/` and installs `chromadb` there:

```bash
python3 "$CODEX_HOME/skills/artifacts/scripts/artifacts_bootstrap_env.py"
```

### 1) Initialize a request workspace

```bash
python3 "$CODEX_HOME/skills/artifacts/scripts/artifacts_init.py" --request "Describe the task request here"
```

This creates:

- `.artifacts/artifacts/{request_id}/plan.md`
- `.artifacts/artifacts/{request_id}/todo.md`
- `.artifacts/artifacts/{request_id}/walkthrough.md`

### 2) Index completed work (also prunes old runs)

```bash
.artifacts/.venv/bin/python "$CODEX_HOME/skills/artifacts/scripts/artifacts_index.py"
```

### 3) Query past work

```bash
.artifacts/.venv/bin/python "$CODEX_HOME/skills/artifacts/scripts/artifacts_query.py" "what did we do about X?"
```

## Configuration

- `ARTIFACTS_TTL_DAYS` (default: `7`): controls retention window used by `artifacts_index.py`.

## Repository layout

The skill itself lives in `artifacts/`:

- `artifacts/SKILL.md`
- `artifacts/scripts/`
- `artifacts/references/`

The per-repo byproducts created by using the skill live in the *target repository* under:

- `.artifacts/`

