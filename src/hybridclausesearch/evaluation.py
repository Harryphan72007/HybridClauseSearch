"""Reviewed query and graded judgment contracts with deterministic ranking metrics."""

from __future__ import annotations

import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hybridclausesearch.contracts import SearchResult


class ReviewedQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0.0"] = "1.0.0"
    query_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    review_date: date
    reviewer: str = Field(min_length=1)
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_ids: tuple[str, ...] = ()


class RelevanceJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0.0"] = "1.0.0"
    query_id: str
    provision_version_id: str
    relevance: int = Field(ge=0, le=3)
    reviewer: str = Field(min_length=1)
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Evaluation(BaseModel):
    query_count: int
    k: int
    recall_at_k: float
    mrr_at_k: float
    ndcg_at_k: float
    zero_hit_queries: int


def evaluate(
    queries: tuple[ReviewedQuery, ...],
    judgments: tuple[RelevanceJudgment, ...],
    runs: dict[str, tuple[SearchResult, ...]],
    *,
    k: int = 10,
) -> Evaluation:
    if k < 1 or not queries:
        raise ValueError("evaluation needs queries and positive k")
    query_ids = [query.query_id for query in queries]
    if len(set(query_ids)) != len(query_ids):
        raise ValueError("duplicate query ID")
    truth: dict[str, dict[str, int]] = {identifier: {} for identifier in query_ids}
    for judgment in judgments:
        if judgment.query_id not in truth:
            raise ValueError("judgment references unknown query")
        query = queries[query_ids.index(judgment.query_id)]
        if judgment.snapshot_sha256 != query.snapshot_sha256:
            raise ValueError("judgment snapshot mismatch")
        if judgment.provision_version_id in truth[judgment.query_id]:
            raise ValueError("duplicate judgment")
        truth[judgment.query_id][judgment.provision_version_id] = judgment.relevance
    totals = [0.0, 0.0, 0.0]
    zero_hits = 0
    for query in queries:
        hits = runs.get(query.query_id, ())
        if not hits:
            zero_hits += 1
        if any(
            hit.snapshot_sha256 != query.snapshot_sha256 or hit.query_id != query.query_id
            for hit in hits
        ):
            raise ValueError("run identity mismatch")
        ids = [hit.provision_version_id for hit in hits]
        if len(set(ids)) != len(ids) or [hit.rank for hit in hits] != list(range(1, len(hits) + 1)):
            raise ValueError("run ranks must be unique and consecutive")
        grades = truth[query.query_id]
        relevant = sum(grade > 0 for grade in grades.values())
        selected = [grades.get(identifier, 0) for identifier in ids[:k]]
        totals[0] += sum(grade > 0 for grade in selected) / relevant if relevant else 0.0
        totals[1] += next((1 / rank for rank, grade in enumerate(selected, 1) if grade > 0), 0.0)
        dcg = sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(selected, 1))
        ideal = sum(
            (2**grade - 1) / math.log2(rank + 1)
            for rank, grade in enumerate(sorted(grades.values(), reverse=True)[:k], 1)
        )
        totals[2] += dcg / ideal if ideal else 0.0
    return Evaluation(
        query_count=len(queries),
        k=k,
        recall_at_k=totals[0] / len(queries),
        mrr_at_k=totals[1] / len(queries),
        ndcg_at_k=totals[2] / len(queries),
        zero_hit_queries=zero_hits,
    )
