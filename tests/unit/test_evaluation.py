from __future__ import annotations

from datetime import date
from pathlib import Path

from hybridclausesearch.bm25 import BM25Index
from hybridclausesearch.contracts import SearchRequest
from hybridclausesearch.evaluation import RelevanceJudgment, ReviewedQuery, evaluate
from hybridclausesearch.snapshot import load_snapshot
from tests.unit.snapshot_fixture import make_snapshot


def test_metrics_include_zero_hit_query(tmp_path: Path) -> None:
    digest = make_snapshot(tmp_path)
    index = BM25Index(load_snapshot(tmp_path, expected_sha256=digest, require_ready=False))
    day = date(2024, 1, 1)
    queries = tuple(
        ReviewedQuery(
            query_id=q,
            text=text,
            review_date=day,
            reviewer="synthetic-test",
            snapshot_sha256=digest,
        )
        for q, text in (("q1", "đất"), ("q2", "absent"))
    )
    judgments = tuple(
        RelevanceJudgment(
            query_id=q.query_id,
            provision_version_id="pv:test",
            relevance=2,
            reviewer="synthetic-test",
            snapshot_sha256=digest,
        )
        for q in queries
    )
    runs = {
        q.query_id: index.search(
            SearchRequest(
                query_id=q.query_id, query=q.text, review_date=day, snapshot_sha256=digest
            )
        )
        for q in queries
    }
    result = evaluate(queries, judgments, runs, k=10)
    assert (result.recall_at_k, result.mrr_at_k, result.ndcg_at_k, result.zero_hit_queries) == (
        0.5,
        0.5,
        0.5,
        1,
    )
