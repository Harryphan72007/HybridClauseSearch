from __future__ import annotations

from pathlib import Path

import pytest

from hybridclausesearch.bm25 import BM25Index
from hybridclausesearch.snapshot import load_snapshot
from hybridclausesearch.storage import load_index, save_index
from tests.unit.snapshot_fixture import make_snapshot


def test_index_roundtrip_and_staleness(tmp_path: Path) -> None:
    root = tmp_path / "snapshot"
    digest = make_snapshot(root)
    snapshot = load_snapshot(root, expected_sha256=digest, require_ready=False)
    path = tmp_path / "index.json"
    save_index(BM25Index(snapshot), path)
    assert load_index(path, snapshot).records == BM25Index(snapshot).records
    with pytest.raises(ValueError, match="already exists"):
        save_index(BM25Index(snapshot), path)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("unicode-nfkc-v1", "unicode-nfkc-v2"), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_index(path, snapshot)
