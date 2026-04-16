from pathlib import Path

from fastapi.testclient import TestClient

from automation.visualization.api import create_agent_canvas_app


def test_agent_canvas_api_overview_and_node() -> None:
    project_root = Path(__file__).resolve().parent.parent
    app = create_agent_canvas_app(project_root)
    client = TestClient(app)

    overview_response = client.get("/api/graph/overview")
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["id"] == "overview"

    node_response = client.get("/api/node/domain.control_plane")
    assert node_response.status_code == 200
    node_payload = node_response.json()
    assert node_payload["label"] == "Control Plane"


def test_agent_canvas_action_run_endpoint_can_be_stubbed() -> None:
    project_root = Path(__file__).resolve().parent.parent
    app = create_agent_canvas_app(project_root)
    client = TestClient(app)

    def fake_start_action(action_id: str) -> dict[str, object]:
        return {
            "run_id": "fake-run",
            "action_id": action_id,
            "label": "Fake",
            "status": "running",
            "started_at": "2026-04-16T00:00:00+00:00",
            "log_path": "artifacts/agent_canvas/actions/fake-run.log",
        }

    app.state.action_registry.start_action = fake_start_action  # type: ignore[method-assign]

    response = client.post("/api/actions/run", json={"action_id": "run_supervisor"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_id"] == "run_supervisor"
    assert payload["status"] == "running"
