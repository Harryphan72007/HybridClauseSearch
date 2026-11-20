"""Versioned, validated search exchange contracts."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0.0"] = "1.0.0"


class Eligibility(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"


class SearchRequest(Contract):
    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_date: date
    jurisdiction: Literal["VN"] = "VN"
    document_ids: tuple[str, ...] = ()
    limit: int = Field(default=10, ge=1, le=1000)
    include_unknown: bool = True


class Citation(Contract):
    source_artifact_id: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    text: str = Field(min_length=1)
    document_id: str
    document_version_id: str
    provision_id: str
    provision_version_id: str
    canonical_path: tuple[str, ...]

    @model_validator(mode="after")
    def valid_offsets(self) -> Citation:
        if self.end_offset <= self.start_offset:
            raise ValueError("citation end must follow start")
        return self


class SearchResult(Contract):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    query_id: str
    provision_version_id: str
    rank: int = Field(ge=1)
    score: float
    component_scores: dict[str, float]
    citation: Citation
    review_date: date
    eligibility: Eligibility
    eligibility_reasons: tuple[str, ...]

    @model_validator(mode="after")
    def citation_identity_matches(self) -> SearchResult:
        if self.citation.provision_version_id != self.provision_version_id:
            raise ValueError("citation and result provision version differ")
        return self
