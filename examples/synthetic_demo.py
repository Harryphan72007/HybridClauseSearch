"""Cross-repository smoke test using VietLegalCorpus's explicitly synthetic golden bundle."""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from vietlegalcorpus.quality import read_bundle
from vietlegalcorpus.snapshot import build_snapshot, validate_snapshot

from hybridclausesearch.bm25 import BM25Index
from hybridclausesearch.contracts import SearchRequest
from hybridclausesearch.snapshot import load_snapshot
from hybridclausesearch.storage import load_index, save_index


def run(corpus_repository: Path, output: Path) -> dict[str, object]:
    bundle = read_bundle(corpus_repository / "data/samples/golden-corpus")
    built = build_snapshot(
        bundle,
        output / "snapshot",
        corpus_id="corpus:synthetic-demo",
        created_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
        review_date=date(2026, 8, 24),
        generator_version="synthetic-demo/1.0.0",
        config_sha256="a" * 64,
    )
    validated = validate_snapshot(output / "snapshot", expected_sha256=built.snapshot_sha256)
    snapshot = load_snapshot(
        output / "snapshot", expected_sha256=validated.snapshot_sha256, require_ready=False
    )
    assert not snapshot.ready, "synthetic fixtures must never be marked source-reviewed"
    index = BM25Index(snapshot)
    save_index(index, output / "index.json")
    restored = load_index(output / "index.json", snapshot)
    # Use a term from the actual synthetic fixture, avoiding a fabricated relevance label.
    query = SearchRequest(
        query_id="synthetic:smoke",
        query=index.records[0].tokens[0],
        review_date=date(2026, 8, 24),
        snapshot_sha256=snapshot.digest,
    )
    hits = restored.search(query)
    assert hits, "synthetic smoke query must retrieve at least one clause"
    evidence = {
        entry["source_artifact_id"]: entry["text"] for entry in snapshot.records["source_evidence"]
    }
    for hit in hits:
        anchor = hit.citation
        assert (
            evidence[anchor.source_artifact_id][anchor.start_offset : anchor.end_offset]
            == anchor.text
        )
    result: dict[str, object] = {
        "fixture": "synthetic golden corpus; no real-law relevance judgments",
        "source_review_ready": snapshot.ready,
        "snapshot_sha256": snapshot.digest,
        "record_count": len(index.records),
        "hit_count": len(hits),
        "provision_version_ids": [hit.provision_version_id for hit in hits],
        "cross_repository_validation": "passed",
    }
    (output / "demo.json").write_text(
        json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: python examples/synthetic_demo.py CORPUS_REPOSITORY EMPTY_OUTPUT_DIR"
        )
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), ensure_ascii=True))
