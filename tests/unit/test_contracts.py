from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from hybridclausesearch.contracts import Citation, Eligibility, SearchRequest, SearchResult


def test_search_contract_preserves_snapshot_and_exact_version() -> None:
    request = SearchRequest(
        query_id="q1",
        query="quyền sử dụng đất",
        snapshot_sha256="a" * 64,
        review_date=date(2024, 1, 1),
    )
    citation = Citation(
        source_artifact_id="artifact:1",
        start_offset=2,
        end_offset=5,
        text="abc",
        document_id="doc:1",
        document_version_id="dv:1",
        provision_id="p:1",
        provision_version_id="pv:1",
        canonical_path=("article:1",),
    )
    result = SearchResult(
        snapshot_sha256=request.snapshot_sha256,
        query_id=request.query_id,
        provision_version_id="pv:1",
        rank=1,
        score=1.0,
        component_scores={"bm25": 1.0},
        citation=citation,
        review_date=request.review_date,
        eligibility=Eligibility.UNKNOWN,
        eligibility_reasons=("date unknown",),
    )
    assert result.citation.document_version_id == "dv:1"
    with pytest.raises(ValidationError, match="citation and result"):
        SearchResult.model_validate({**result.model_dump(), "provision_version_id": "pv:other"})
    with pytest.raises(ValidationError):
        SearchRequest.model_validate({**request.model_dump(), "schema_version": "2.0.0"})
