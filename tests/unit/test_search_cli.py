from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hybridclausesearch.cli import app
from tests.unit.snapshot_fixture import make_snapshot


def test_cli_indexes_and_searches_synthetic_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    digest = make_snapshot(root)
    index = tmp_path / "index.json"
    runner = CliRunner()
    built = runner.invoke(app, ["index", str(root), str(index), "--expected-sha256", digest, "--synthetic-development"])
    assert built.exit_code == 0, built.output
    searched = runner.invoke(app, ["search", str(root), str(index), "chuyển nhượng", "--expected-sha256", digest, "--review-date", "2024-01-01", "--synthetic-development"])
    assert searched.exit_code == 0, searched.output
    assert json.loads(searched.stdout)["results"][0]["provision_version_id"] == "pv:test"


def test_cli_rejects_unreviewed_snapshot_by_default(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    digest = make_snapshot(root)
    response = CliRunner().invoke(app, ["index", str(root), str(tmp_path / "index.json"), "--expected-sha256", digest])
    assert response.exit_code == 1
    assert "pending" in response.output
