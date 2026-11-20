from __future__ import annotations

from datetime import date

from hybridclausesearch.contracts import Eligibility, SearchRequest
from hybridclausesearch.filters import assess


def test_date_scope_and_unknown_remain_distinct() -> None:
    request = SearchRequest(query_id="q", query="đất", snapshot_sha256="a" * 64, review_date=date(2024, 1, 1))
    version = {"document_version_id": "dv:1", "document_id": "doc:1", "effective_from": "2020-01-01", "status": "in_force"}
    document = {"jurisdiction": "VN"}
    assert assess(version, document, request)[0] == Eligibility.ELIGIBLE
    assert assess({**version, "status": "repealed"}, document, request)[0] == Eligibility.UNKNOWN
    assert assess({**version, "effective_from": None}, document, request)[0] == Eligibility.UNKNOWN
    assert assess(version, document, request, ({"relation_type": "repeals", "target": {"record_id": "dv:1"}, "effective_from": "2023-01-01"},))[0] == Eligibility.INELIGIBLE
    assert assess(version, {"jurisdiction": "OTHER"}, request)[0] == Eligibility.INELIGIBLE
