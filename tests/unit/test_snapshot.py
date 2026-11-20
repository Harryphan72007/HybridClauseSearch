from __future__ import annotations

from pathlib import Path

import pytest

from hybridclausesearch.snapshot import SnapshotError, load_snapshot
from tests.unit.snapshot_fixture import make_snapshot


def test_snapshot_requires_trusted_checksum_and_explicit_development_mode(tmp_path: Path) -> None:
    digest = make_snapshot(tmp_path)
    with pytest.raises(SnapshotError, match="trusted checksum"):
        load_snapshot(tmp_path, expected_sha256="0" * 64)
    with pytest.raises(SnapshotError, match="pending"):
        load_snapshot(tmp_path, expected_sha256=digest)
    snapshot = load_snapshot(tmp_path, expected_sha256=digest, require_ready=False)
    assert snapshot.digest == digest
    assert snapshot.ready is False


def test_snapshot_rejects_tampered_evidence(tmp_path: Path) -> None:
    digest = make_snapshot(tmp_path)
    (tmp_path / "records/source_evidence.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(SnapshotError, match="evidence checksum"):
        load_snapshot(tmp_path, expected_sha256=digest, require_ready=False)
