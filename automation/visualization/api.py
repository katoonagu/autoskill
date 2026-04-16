from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from automation.paths import artifacts_root, resolve_repo_path

from .actions import ActionRegistry
from .manifest_builder import build_agent_canvas_bundle, write_agent_canvas_bundle


class ActionRunRequest(BaseModel):
    action_id: str


def _resolve_safe_path(project_root: Path, raw_path: str) -> Path:
    candidate = resolve_repo_path(project_root, raw_path).resolve()
    root = project_root.resolve()
    if root not in candidate.parents and candidate != root:
        raise HTTPException(status_code=400, detail="Path escapes project root")
    return candidate


def create_agent_canvas_app(project_root: Path) -> FastAPI:
    app = FastAPI(title="Agent Canvas Dashboard", version="0.1.0")
    app.state.project_root = project_root
    app.state.action_registry = ActionRegistry(project_root)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/graph/overview")
    def get_overview() -> JSONResponse:
        bundle = write_agent_canvas_bundle(
            app.state.project_root,
            action_registry=app.state.action_registry,
        )
        return JSONResponse(bundle["overview"])

    @app.get("/api/graph/domain/{domain_id}")
    def get_domain(domain_id: str) -> JSONResponse:
        bundle = build_agent_canvas_bundle(
            app.state.project_root,
            action_registry=app.state.action_registry,
        )
        if domain_id not in bundle["domains"]:
            raise HTTPException(status_code=404, detail="Unknown domain")
        return JSONResponse(bundle["domains"][domain_id])

    @app.get("/api/node/{node_id}")
    def get_node(node_id: str) -> JSONResponse:
        bundle = build_agent_canvas_bundle(
            app.state.project_root,
            action_registry=app.state.action_registry,
        )
        if node_id not in bundle["nodes"]:
            raise HTTPException(status_code=404, detail="Unknown node")
        return JSONResponse(bundle["nodes"][node_id])

    @app.get("/api/actions")
    def get_actions() -> JSONResponse:
        return JSONResponse(app.state.action_registry.list_actions())

    @app.post("/api/actions/run")
    def run_action(request: ActionRunRequest) -> JSONResponse:
        try:
            run = app.state.action_registry.start_action(request.action_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown action: {request.action_id}") from exc
        write_agent_canvas_bundle(
            app.state.project_root,
            action_registry=app.state.action_registry,
        )
        return JSONResponse(run)

    @app.get("/api/actions/runs")
    def get_action_runs() -> JSONResponse:
        return JSONResponse(app.state.action_registry.refresh_runs())

    @app.get("/api/file")
    def get_file(path: str = Query(...)) -> PlainTextResponse:
        candidate = _resolve_safe_path(app.state.project_root, path)
        if not candidate.exists() or not candidate.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return PlainTextResponse(candidate.read_text(encoding="utf-8", errors="replace"))

    @app.get("/api/dir")
    def get_dir(path: str = Query(...)) -> JSONResponse:
        candidate = _resolve_safe_path(app.state.project_root, path)
        if not candidate.exists() or not candidate.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        items = []
        for entry in sorted(candidate.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            items.append(
                {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "path": str(entry.resolve().relative_to(app.state.project_root.resolve()).as_posix()),
                }
            )
        return JSONResponse({"path": path, "items": items})

    @app.get("/api/manifest/rebuild")
    def rebuild_manifest() -> JSONResponse:
        bundle = write_agent_canvas_bundle(
            app.state.project_root,
            action_registry=app.state.action_registry,
        )
        manifest_path = artifacts_root(app.state.project_root) / "agent_canvas" / "graph_manifest.json"
        return JSONResponse({"manifest_path": manifest_path.relative_to(app.state.project_root).as_posix(), "generated_at": bundle["generated_at"]})

    return app
