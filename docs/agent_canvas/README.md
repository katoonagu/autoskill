# Agent Canvas

Local dashboard for the repo runtime and artifacts.

## What it shows

- overview graph across control plane, company research, outreach, browser runtime, and reports
- drill-down graph per domain
- live polling against current JSON/YAML/MD state
- markdown drawer per node with source-of-truth links
- safe launch buttons for a small whitelist of top-level jobs

## Run backend

```bash
python scripts/run_agent_canvas.py
```

The API listens on `http://127.0.0.1:8000`.

## Run frontend

```bash
cd apps/agent-canvas
npm install
npm run dev
```

The frontend listens on `http://127.0.0.1:5173`.

## Rebuild manifest only

```bash
python scripts/admin/write_agent_canvas_manifest.py
```

This writes:

- `artifacts/agent_canvas/graph_manifest.json`
- `artifacts/agent_canvas/domain_<id>.json`
- `artifacts/agent_canvas/node_index.json`
- `artifacts/agent_canvas/action_runs.json`
