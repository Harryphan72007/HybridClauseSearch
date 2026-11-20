"""Read the published CorpusSnapshot v1 format with independent integrity checks."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SnapshotError(ValueError):
    """An input snapshot is unsupported, untrusted, or internally inconsistent."""


class _Record(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str = "1.0.0"


class _Entry(BaseModel):
    record_type: str
    relative_path: str
    sha256: str
    record_count: int = Field(ge=0)


class _Manifest(_Record):
    corpus_id: str
    review_date: str
    source_evidence_sha256: str
    readiness_sha256: str
    source_review_sha256: str | None = None
    entries: list[_Entry]


_FILES = {
    "source_artifacts": ("source_artifacts.jsonl", "source_artifact", "artifact_id"),
    "documents": ("legal_documents.jsonl", "legal_document", "document_id"),
    "document_versions": ("document_versions.jsonl", "document_version", "document_version_id"),
    "provisions": ("provisions.jsonl", "provision", "provision_id"),
    "provision_versions": ("provision_versions.jsonl", "provision_version", "provision_version_id"),
    "relation_edges": ("relation_edges.jsonl", "relation_edge", "relation_id"),
}


@dataclass(frozen=True)
class CorpusSnapshot:
    digest: str
    corpus_id: str
    review_date: str
    ready: bool
    records: dict[str, tuple[dict[str, Any], ...]]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if not relative or "\\" in relative or posix.is_absolute() or any(
        part in (".", "..") for part in relative.split("/")
    ) or re.match(r"^[A-Za-z]:", relative):
        raise SnapshotError(f"unsafe snapshot path: {relative}")
    target = root.joinpath(*posix.parts)
    if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
        raise SnapshotError(f"snapshot path escapes root: {relative}")
    return target


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_snapshot(
    root: Path, *, expected_sha256: str, require_ready: bool = True
) -> CorpusSnapshot:
    """Require an independently supplied manifest hash, then validate all snapshot files.

    Development fixtures may set ``require_ready=False``; this never fabricates review.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise SnapshotError("expected_sha256 must be a lowercase SHA-256 digest")
    try:
        manifest_bytes = _path(root, "manifest.json").read_bytes()
        digest = _sha(manifest_bytes)
        if digest != expected_sha256:
            raise SnapshotError("snapshot does not match the trusted checksum")
        manifest = _Manifest.model_validate_json(manifest_bytes)
        if manifest.schema_version != "1.0.0":
            raise SnapshotError("unsupported corpus schema version")
        if _path(root, "snapshot.sha256").read_text(encoding="ascii").strip() != digest:
            raise SnapshotError("snapshot checksum file disagrees with manifest")
        entries = {entry.relative_path: entry for entry in manifest.entries}
        if len(entries) != len(manifest.entries) or list(entries) != sorted(entries):
            raise SnapshotError("manifest paths must be unique and sorted")
        for entry in manifest.entries:
            path = _path(root, entry.relative_path)
            data = path.read_bytes()
            if _sha(data) != entry.sha256:
                raise SnapshotError(f"checksum mismatch: {entry.relative_path}")
            if entry.relative_path.startswith("records/"):
                if len([line for line in data.splitlines() if line.strip()]) != entry.record_count:
                    raise SnapshotError(f"record count mismatch: {entry.relative_path}")
            elif entry.record_count != 1:
                raise SnapshotError(f"artifact count mismatch: {entry.relative_path}")
        records: dict[str, tuple[dict[str, Any], ...]] = {}
        for family, (filename, kind, key) in _FILES.items():
            relative = f"records/{filename}"
            if relative not in entries or entries[relative].record_type != kind:
                raise SnapshotError(f"missing or mistyped record file: {relative}")
            items = tuple(json.loads(line) for line in _path(root, relative).read_text(
                encoding="utf-8"
            ).splitlines() if line.strip())
            ids = [item[key] for item in items]
            if ids != sorted(set(ids)) or any(item.get("schema_version") != "1.0.0" for item in items):
                raise SnapshotError(f"invalid IDs or schema version: {relative}")
            records[family] = items
        evidence_path = _path(root, "records/source_evidence.jsonl")
        if _sha(evidence_path.read_bytes()) != manifest.source_evidence_sha256:
            raise SnapshotError("source evidence checksum mismatch")
        records["source_evidence"] = tuple(json.loads(line) for line in evidence_path.read_text(
            encoding="utf-8"
        ).splitlines() if line.strip())
        readiness_path = _path(root, "g1_readiness.json")
        if _sha(readiness_path.read_bytes()) != manifest.readiness_sha256:
            raise SnapshotError("readiness checksum mismatch")
        readiness = _read_json(readiness_path)
        if manifest.source_review_sha256 is not None:
            if _sha(_path(root, "source_review.json").read_bytes()) != manifest.source_review_sha256:
                raise SnapshotError("source review checksum mismatch")
        expected_paths = set(entries) | {"manifest.json", "snapshot.sha256", "g1_readiness.json", "records/source_evidence.jsonl"}
        if manifest.source_review_sha256:
            expected_paths.add("source_review.json")
        actual_paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        if actual_paths != expected_paths:
            raise SnapshotError("snapshot has missing or unlisted files")
        artifacts = {item["artifact_id"]: item for item in records["source_artifacts"]}
        versions = {item["document_version_id"]: item for item in records["document_versions"]}
        provisions = {item["provision_id"]: item for item in records["provisions"]}
        evidence = {item["source_artifact_id"]: item["text"] for item in records["source_evidence"]}
        if len(evidence) != len(records["source_evidence"]):
            raise SnapshotError("duplicate source evidence")
        for artifact in artifacts.values():
            path = artifact["storage_path"]
            if path not in entries or entries[path].sha256 != artifact["sha256"] or artifact["byte_length"] != _path(root, path).stat().st_size:
                raise SnapshotError("source artifact inventory mismatch")
        for item in records["provision_versions"]:
            parent = versions[item["document_version_id"]]
            logical = provisions[item["provision_id"]]
            anchor = item["source_anchor"]
            source = evidence[anchor["source_artifact_id"]]
            if (logical["document_id"] != parent["document_id"] or
                anchor["source_artifact_id"] != parent["source_artifact_id"] or
                source[anchor["start_offset"]:anchor["end_offset"]] != item["text"]):
                raise SnapshotError("provision reference or citation span mismatch")
        if require_ready and not readiness["ready"]:
            raise SnapshotError("G1 source review is pending; use development mode for synthetic fixtures")
        return CorpusSnapshot(digest, manifest.corpus_id, manifest.review_date, bool(readiness["ready"]), records)
    except (OSError, KeyError, TypeError, ValueError, ValidationError) as exc:
        if isinstance(exc, SnapshotError):
            raise
        raise SnapshotError(f"invalid CorpusSnapshot: {exc}") from exc
