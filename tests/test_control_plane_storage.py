from automation.control_plane.storage import ensure_control_plane_layout


def test_ensure_control_plane_layout_uses_runtime_and_artifacts(tmp_path) -> None:
    paths = ensure_control_plane_layout(tmp_path)

    assert paths.tasks_root == tmp_path / "runtime" / "tasks"
    assert paths.decisions_root == tmp_path / "runtime" / "decisions"
    assert paths.state_root == tmp_path / "runtime" / "state"
    assert paths.output_root == tmp_path / "artifacts" / "supervisor"
