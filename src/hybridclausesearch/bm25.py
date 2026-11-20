"""Deterministic BM25 lexical ranking over validated clause records."""

from __future__ import annotations

import math
from collections import Counter

from hybridclausesearch.contracts import Eligibility, SearchRequest, SearchResult
from hybridclausesearch.filters import assess
from hybridclausesearch.records import ClauseRecord, build_records, tokenize
from hybridclausesearch.snapshot import CorpusSnapshot

K1 = 1.2
B = 0.75


class BM25Index:
    def __init__(self, snapshot: CorpusSnapshot, records: tuple[ClauseRecord, ...] | None = None):
        self.snapshot = snapshot
        self.records = build_records(snapshot) if records is None else records
        self.versions = {v["document_version_id"]: v for v in snapshot.records["document_versions"]}
        self.documents = {d["document_id"]: d for d in snapshot.records["documents"]}
        self.relations = snapshot.records["relation_edges"]
        self.counts = tuple(Counter(record.tokens) for record in self.records)
        self.df = Counter(token for counts in self.counts for token in counts)
        self.avgdl = sum(len(r.tokens) for r in self.records) / len(self.records) if self.records else 0.0

    def search(self, request: SearchRequest) -> tuple[SearchResult, ...]:
        if request.snapshot_sha256 != self.snapshot.digest:
            raise ValueError("request snapshot checksum does not match the index")
        query = set(tokenize(request.query))
        if not query:
            return ()
        hits = []
        size = len(self.records)
        for record, counts in zip(self.records, self.counts, strict=True):
            version = self.versions[record.citation.document_version_id]
            document = self.documents[record.citation.document_id]
            eligibility, reasons = assess(version, document, request, self.relations)
            if eligibility == Eligibility.INELIGIBLE or (eligibility == Eligibility.UNKNOWN and not request.include_unknown):
                continue
            score = 0.0
            for token in query:
                frequency = counts[token]
                if frequency:
                    idf = math.log1p((size - self.df[token] + 0.5) / (self.df[token] + 0.5))
                    length = len(record.tokens) / self.avgdl if self.avgdl else 0.0
                    score += idf * frequency * (K1 + 1) / (frequency + K1 * (1 - B + B * length))
            if score > 0:
                hits.append((score, record, eligibility, reasons))
        hits.sort(key=lambda hit: (-hit[0], hit[1].citation.provision_version_id))
        return tuple(SearchResult(
            snapshot_sha256=self.snapshot.digest, query_id=request.query_id,
            provision_version_id=record.citation.provision_version_id, rank=rank,
            score=score, component_scores={"bm25": score}, citation=record.citation,
            review_date=request.review_date, eligibility=eligibility,
            eligibility_reasons=reasons,
        ) for rank, (score, record, eligibility, reasons) in enumerate(hits[:request.limit], 1))
