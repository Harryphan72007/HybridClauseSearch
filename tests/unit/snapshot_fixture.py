"""Tiny explicitly synthetic CorpusSnapshot for adapter and search behavior tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _write(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def make_snapshot(root: Path) -> str:
    source = "Điều 1. Quyền sử dụng đất\n1. Người sử dụng đất có quyền chuyển nhượng.\n"
    clause = "1. Người sử dụng đất có quyền chuyển nhượng."
    offset = source.index(clause)

    def sha(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    artifact = "artifact:test"
    records: dict[str, list[dict[str, Any]]] = {
        "source_artifacts": [
            {
                "schema_version": "1.0.0",
                "artifact_id": artifact,
                "sha256": sha(source.encode()),
                "byte_length": len(source.encode()),
                "storage_path": "artifacts/source.txt",
            }
        ],
        "documents": [
            {
                "schema_version": "1.0.0",
                "document_id": "doc:test",
                "title": "Luật thử nghiệm",
                "jurisdiction": "VN",
            }
        ],
        "document_versions": [
            {
                "schema_version": "1.0.0",
                "document_version_id": "version:test",
                "document_id": "doc:test",
                "source_artifact_id": artifact,
                "effective_from": "2020-01-01",
                "effective_to": None,
                "status": "in_force",
            }
        ],
        "provisions": [
            {
                "schema_version": "1.0.0",
                "provision_id": "provision:test",
                "document_id": "doc:test",
                "kind": "clause",
                "canonical_path": ["article:1", "clause:1"],
                "label": "Khoản 1",
                "parent_provision_id": None,
            }
        ],
        "provision_versions": [
            {
                "schema_version": "1.0.0",
                "provision_version_id": "pv:test",
                "provision_id": "provision:test",
                "document_version_id": "version:test",
                "text": clause,
                "source_anchor": {
                    "source_artifact_id": artifact,
                    "start_offset": offset,
                    "end_offset": offset + len(clause),
                },
            }
        ],
        "relation_edges": [],
    }
    entries: list[dict[str, Any]] = []
    kinds = {
        "source_artifacts": "source_artifact",
        "documents": "legal_document",
        "document_versions": "document_version",
        "provisions": "provision",
        "provision_versions": "provision_version",
        "relation_edges": "relation_edge",
    }
    names = {**{key: key for key in records}, "documents": "legal_documents"}
    for family, items in records.items():
        relative = f"records/{names[family]}.jsonl"
        digest = _write(
            root / relative,
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items).encode(),
        )
        entries.append(
            {
                "record_type": kinds[family],
                "relative_path": relative,
                "sha256": digest,
                "record_count": len(items),
            }
        )
    artifact_digest = _write(root / "artifacts/source.txt", source.encode())
    entries.append(
        {
            "record_type": "source_artifact",
            "relative_path": "artifacts/source.txt",
            "sha256": artifact_digest,
            "record_count": 1,
        }
    )
    evidence_digest = _write(
        root / "records/source_evidence.jsonl",
        (
            json.dumps({"source_artifact_id": artifact, "text": source}, ensure_ascii=False) + "\n"
        ).encode(),
    )
    readiness_digest = _write(root / "g1_readiness.json", b'{"ready":false}\n')
    manifest = {
        "schema_version": "1.0.0",
        "corpus_id": "corpus:synthetic",
        "review_date": "2026-08-24",
        "source_evidence_sha256": evidence_digest,
        "readiness_sha256": readiness_digest,
        "entries": sorted(entries, key=lambda item: str(item["relative_path"])),
    }
    digest = _write(root / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode())
    _write(root / "snapshot.sha256", (digest + "\n").encode())
    return digest
