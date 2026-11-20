from __future__ import annotations

from datetime import date
from pathlib import Path

from hybridclausesearch.bm25 import BM25Index
from hybridclausesearch.contracts import SearchRequest
from hybridclausesearch.snapshot import load_snapshot
from tests.unit.snapshot_fixture import make_snapshot


def test_ranked_retrieval_and_zero_hits(tmp_path: Path) -> None:
    digest = make_snapshot(tmp_path)
    index = BM25Index(load_snapshot(tmp_path, expected_sha256=digest, require_ready=False))
    request = SearchRequest(
        query_id="q",
        query="chuyển nhượng đất",
        snapshot_sha256=digest,
        review_date=date(2024, 1, 1),
    )
    hits = index.search(request)
    assert [(h.rank, h.provision_version_id) for h in hits] == [(1, "pv:test")]
    assert hits[0].citation.text == "1. Người sử dụng đất có quyền chuyển nhượng."
    assert index.search(request.model_copy(update={"query": "xyzabsent"})) == ()
    assert index.search(request.model_copy(update={"review_date": date(2019, 1, 1)})) == ()
