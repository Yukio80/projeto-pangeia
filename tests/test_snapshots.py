from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pangeia.api.server import app
from pangeia.mcp_server import (
    handle_read_resource,
    handle_list_resources,
)

client = TestClient(app)


# ─── Helpers ──────────────────────────────────────────────────


def _write_snapshot(tmp_path: Path, tick: int, label: str = "", extra: dict | None = None):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    suffix = f"_{label}" if label else ""
    data = {
        "tick": tick,
        "snapshot_timestamp": "2026-01-01T00:00:00",
        "snapshot_label": label,
        **({} if extra is None else extra),
    }
    path = snap_dir / f"{tick:06d}{suffix}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ─── POST /snapshot ───────────────────────────────────────────


def test_snapshot_creates_json_file(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.post("/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] >= 0
    assert data["size_bytes"] > 0
    assert data["label"] == ""
    assert "timestamp" in data
    assert (tmp_path / "snapshots").is_dir()
    files = list((tmp_path / "snapshots").glob("*.json"))
    assert len(files) == 1


def test_snapshot_filename_includes_tick_with_6_digits(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.post("/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    expected_name = f"{data['tick']:06d}.json"
    assert data["path"].endswith(expected_name)


def test_snapshot_filename_includes_label(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.post("/snapshot?label=pre_colapso")
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "pre_colapso"
    assert "pre_colapso" in data["path"]


def test_snapshot_returns_snapshot_response(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.post("/snapshot?label=teste")
    assert resp.status_code == 200
    data = resp.json()
    assert "tick" in data
    assert "path" in data
    assert "size_bytes" in data
    assert "timestamp" in data
    assert "label" in data


def test_snapshot_creates_directory_if_not_exists(tmp_path, monkeypatch):
    snap_dir = tmp_path / "novo_snapshots"
    assert not snap_dir.is_dir()
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.post("/snapshot")
    assert resp.status_code == 200
    assert snap_dir.is_dir()


# ─── GET /snapshots ───────────────────────────────────────────


def test_list_snapshots_returns_empty_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "inexistente")
    resp = client.get("/snapshots")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_snapshots_returns_metadata(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 100, "alpha")
    _write_snapshot(tmp_path, 200, "beta")
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/snapshots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["tick"] == 100
    assert data[1]["tick"] == 200
    for item in data:
        assert "filename" in item
        assert "size_bytes" in item
        assert "timestamp" in item
        assert "label" in item


def test_list_snapshots_sorted_by_tick(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 50)
    _write_snapshot(tmp_path, 10)
    _write_snapshot(tmp_path, 200)
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/snapshots")
    assert resp.status_code == 200
    ticks = [s["tick"] for s in resp.json()]
    assert ticks == [10, 50, 200]


# ─── GET /snapshot/{tick} ─────────────────────────────────────


def test_get_snapshot_returns_content(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 42, extra={"economy": {"gdp": 100.0}})
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/snapshot/42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] == 42
    assert data["economy"]["gdp"] == 100.0


def test_get_snapshot_404_when_tick_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.get("/snapshot/999")
    assert resp.status_code == 404


def test_get_snapshot_returns_latest_when_duplicate_tick(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 50, label="early", extra={"version": 1})
    _write_snapshot(tmp_path, 50, label="late", extra={"version": 2})
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/snapshot/50")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


# ─── GET /timeline ────────────────────────────────────────────


def test_timeline_extracts_gdp_from_multiple_snapshots(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 10, extra={"economy": {"indicators": {"gdp": 50.0}}})
    _write_snapshot(tmp_path, 20, extra={"economy": {"indicators": {"gdp": 80.0}}})
    _write_snapshot(tmp_path, 30, extra={"economy": {"indicators": {"gdp": 120.0}}})
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/timeline?metric=gdp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "gdp"
    assert len(data["points"]) == 3
    assert data["points"] == [
        {"tick": 10, "value": 50.0},
        {"tick": 20, "value": 80.0},
        {"tick": 30, "value": 120.0},
    ]


def test_timeline_skips_snapshot_without_metric(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 10, extra={"economy": {"indicators": {"gdp": 50.0}}})
    _write_snapshot(tmp_path, 20, extra={"no_economy": True})
    _write_snapshot(tmp_path, 30, extra={"economy": {"indicators": {"gdp": 100.0}}})
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/timeline?metric=gdp")
    assert resp.status_code == 200
    data = resp.json()
    points = data["points"]
    assert len(points) == 3
    assert points[0] == {"tick": 10, "value": 50.0}
    assert points[1] == {"tick": 20, "value": None}
    assert points[2] == {"tick": 30, "value": 100.0}


def test_timeline_filters_by_tick_range(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 10, extra={"economy": {"indicators": {"gdp": 10.0}}})
    _write_snapshot(tmp_path, 20, extra={"economy": {"indicators": {"gdp": 20.0}}})
    _write_snapshot(tmp_path, 30, extra={"economy": {"indicators": {"gdp": 30.0}}})
    _write_snapshot(tmp_path, 40, extra={"economy": {"indicators": {"gdp": 40.0}}})
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", snap_dir)
    resp = client.get("/timeline?metric=gdp&from_tick=15&to_tick=35")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["points"]) == 2
    assert data["points"][0] == {"tick": 20, "value": 20.0}
    assert data["points"][1] == {"tick": 30, "value": 30.0}


def test_timeline_empty_when_no_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "vazio")
    resp = client.get("/timeline?metric=gdp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_count"] == 0
    assert data["points"] == []


def test_timeline_returns_400_for_invalid_metric(tmp_path, monkeypatch):
    monkeypatch.setattr("pangeia.api.server._SNAPSHOT_DIR", tmp_path / "snapshots")
    resp = client.get("/timeline?metric=invalid")
    assert resp.status_code == 400


# ─── MCP Resource: pangeia://snapshots ────────────────────────


@pytest.mark.asyncio
async def test_mcp_snapshots_returns_json_list(tmp_path, monkeypatch):
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    _write_snapshot(tmp_path, 10, label="a")
    _write_snapshot(tmp_path, 20, label="b")
    monkeypatch.setattr("pathlib.Path", lambda *a: snap_dir if "snapshots" in str(a) else Path(*a))
    result = await handle_read_resource("pangeia://snapshots")
    data = json.loads(result[0].text)
    assert "snapshots" in data
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_mcp_snapshots_error_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path", lambda *a: tmp_path / "no_snapshots" if "snapshots" in str(a) else Path(*a))
    result = await handle_read_resource("pangeia://snapshots")
    data = json.loads(result[0].text)
    assert "error" in data
    assert "No snapshots found" in data["error"]


# ─── MCP Resource: pangeia://timeline/{metric} ───────────────


@pytest.mark.asyncio
async def test_mcp_timeline_gdp_calls_api(monkeypatch):
    async def fake_api_get(path):
        if "timeline" in path:
            return {"metric": "gdp", "snapshot_count": 2, "points": [{"tick": 10, "value": 50.0}, {"tick": 20, "value": 80.0}]}
        return {}
    import pangeia.mcp_server
    monkeypatch.setattr(pangeia.mcp_server, "_api_get", fake_api_get)
    result = await handle_read_resource("pangeia://timeline/gdp")
    data = json.loads(result[0].text)
    assert data["metric"] == "gdp"
    assert data["snapshot_count"] == 2
    assert len(data["points"]) == 2


@pytest.mark.asyncio
async def test_mcp_timeline_invalid_metric_returns_error():
    result = await handle_read_resource("pangeia://timeline/invalida")
    data = json.loads(result[0].text)
    assert "error" in data
    assert "valid_metrics" in data


# ─── Analyst: PangeiaContext timelines ────────────────────────


@pytest.mark.asyncio
async def test_analyst_collect_includes_timelines_key():
    from pangeia.analyst import PangeiaContext
    ctx = PangeiaContext()
    data = await ctx.collect()
    assert "timelines" in data
    await ctx.close()


@pytest.mark.asyncio
async def test_analyst_collect_timeline_does_not_fail_on_error():
    from pangeia.analyst import PangeiaContext
    ctx = PangeiaContext(base_url="http://localhost:1")
    data = await ctx.collect()
    assert "timelines" in data
    await ctx.close()
