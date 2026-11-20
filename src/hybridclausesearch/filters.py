"""Conservative as-of and scope decisions; never upgrade missing evidence to eligible."""

from __future__ import annotations

from datetime import date
from typing import Any

from hybridclausesearch.contracts import Eligibility, SearchRequest


def assess(
    version: dict[str, Any],
    document: dict[str, Any],
    request: SearchRequest,
    relations: tuple[dict[str, Any], ...] = (),
) -> tuple[Eligibility, tuple[str, ...]]:
    if document.get("jurisdiction") != request.jurisdiction:
        return Eligibility.INELIGIBLE, ("jurisdiction outside requested scope",)
    if request.document_ids and version["document_id"] not in request.document_ids:
        return Eligibility.INELIGIBLE, ("document outside requested scope",)
    target = version["document_version_id"]
    for edge in relations:
        if (
            edge.get("relation_type") in ("repeals", "replaces")
            and edge.get("target", {}).get("record_id") == target
        ):
            when = edge.get("effective_from")
            if when is None:
                return Eligibility.UNKNOWN, ("undated consequential relation",)
            if date.fromisoformat(when) <= request.review_date:
                return Eligibility.INELIGIBLE, (f"{edge['relation_type']} effective {when}",)
    start = version.get("effective_from")
    end = version.get("effective_to")
    if start is None:
        return Eligibility.UNKNOWN, ("effective_from unknown",)
    if request.review_date < date.fromisoformat(start):
        return Eligibility.INELIGIBLE, ("review date precedes effective_from",)
    if end and request.review_date >= date.fromisoformat(end):
        return Eligibility.INELIGIBLE, ("review date is on or after effective_to",)
    status = version.get("status", "unknown")
    if status in ("unknown", "partially_in_force"):
        return Eligibility.UNKNOWN, (f"status {status} is uncertain",)
    if status in ("repealed", "expired", "suspended", "not_yet_effective"):
        # A present status alone does not establish its historical transition date.
        return Eligibility.UNKNOWN, (f"status {status} has no dated historical transition",)
    return Eligibility.ELIGIBLE, ("dated interval and explicit in_force status",)
