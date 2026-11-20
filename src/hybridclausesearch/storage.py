"""Portable index artifact bound to a validated snapshot and tokenizer settings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hybridclausesearch.bm25 import K1, B, BM25Index
from hybridclausesearch.contracts import Citation
from hybridclausesearch.records import ClauseRecord
from hybridclausesearch.snapshot import CorpusSnapshot

INDEX_VERSION = "1.0.0"
TOKENIZER_VERSION = "unicode-nfkc-v1"


def save_index(index: BM25Index, path: Path) -> None:
    if path.exists():
        raise ValueError("index output already exists")
    payload = {
        "index_version": INDEX_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "snapshot_sha256": index.snapshot.digest,
        "bm25": {"k1": K1, "b": B},
        "records": [
            {
                "citation": record.citation.model_dump(mode="json"),
                "tokens": record.tokens,
                "document_title": record.document_title,
                "parent_context": record.parent_context,
            }
            for record in index.records
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    wrapper = {"sha256": hashlib.sha256(body).hexdigest(), "payload": payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise ValueError("temporary index output already exists")
    try:
        temporary.write_text(
            json.dumps(wrapper, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.rename(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_index(path: Path, snapshot: CorpusSnapshot) -> BM25Index:
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    payload = wrapper["payload"]
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(body).hexdigest() != wrapper["sha256"]:
        raise ValueError("index checksum mismatch")
    if (
        payload["index_version"] != INDEX_VERSION
        or payload["tokenizer_version"] != TOKENIZER_VERSION
        or payload["bm25"] != {"k1": K1, "b": B}
        or payload["snapshot_sha256"] != snapshot.digest
    ):
        raise ValueError("stale index: rebuild against this snapshot and configuration")
    records = tuple(
        ClauseRecord(
            Citation.model_validate(item["citation"]),
            tuple(item["tokens"]),
            item["document_title"],
            item["parent_context"],
        )
        for item in payload["records"]
    )
    # Validation of the pinned snapshot precedes this call. Recompute the records to
    # reject semantically altered index data even when the wrapper hash is rewritten.
    from hybridclausesearch.records import build_records

    if records != build_records(snapshot):
        raise ValueError("index records disagree with validated snapshot")
    return BM25Index(snapshot, records)
