from __future__ import annotations

from pathlib import Path

from hybridclausesearch.records import build_records, tokenize
from hybridclausesearch.snapshot import load_snapshot
from tests.unit.snapshot_fixture import make_snapshot


def test_tokens_and_exact_citation(tmp_path: Path) -> None:
    digest = make_snapshot(tmp_path)
    records = build_records(load_snapshot(tmp_path, expected_sha256=digest, require_ready=False))
    assert tokenize("KHÔNG chuyển nhượng 12/2024") == ("không", "chuyển", "nhượng", "12/2024")
    assert len(records) == 1
    assert records[0].citation.text == "1. Người sử dụng đất có quyền chuyển nhượng."
    assert "luật" in records[0].tokens
