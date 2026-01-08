# Artifacts format (repo-local)

## Folder layout

- `.artifacts/artifacts/{request_id}/manifest.json`
- `.artifacts/artifacts/{request_id}/plan.md`
- `.artifacts/artifacts/{request_id}/todo.md`
- `.artifacts/artifacts/{request_id}/walkthrough.md`

## manifest.json fields

- `request_id`: stable id used as the ChromaDB document id
- `created_at`: UTC ISO timestamp
- `updated_at`: UTC ISO timestamp
- `status`: `pending_confirmation` | `in_progress` | `completed` | `blocked`
- `request`: raw user request text

## ChromaDB + environment location

- Persistent ChromaDB: `.artifacts/chroma_db/`
- Required Python environment: `.artifacts/` (e.g. `.artifacts/.venv/`), so all skill byproducts stay under `.artifacts/`
- Collection name: `artifacts`
- TTL retention: 7 days (configurable via `ARTIFACTS_TTL_DAYS`)
