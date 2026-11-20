"""Clause-level records with normalized Vietnamese tokens and exact citations."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from hybridclausesearch.contracts import Citation
from hybridclausesearch.snapshot import CorpusSnapshot


def tokenize(text: str) -> tuple[str, ...]:
    """Preserve Vietnamese diacritics, numbers, document identifiers and negation."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(re.findall(r"[^\W_]+(?:[/-][^\W_]+)*", normalized, flags=re.UNICODE))


@dataclass(frozen=True)
class ClauseRecord:
    citation: Citation
    tokens: tuple[str, ...]
    document_title: str
    parent_context: str


def build_records(snapshot: CorpusSnapshot) -> tuple[ClauseRecord, ...]:
    families = snapshot.records
    documents = {item["document_id"]: item for item in families["documents"]}
    versions = {item["document_version_id"]: item for item in families["document_versions"]}
    provisions = {item["provision_id"]: item for item in families["provisions"]}
    texts = {item["provision_id"]: item["text"] for item in families["provision_versions"]}
    evidence = {item["source_artifact_id"]: item["text"] for item in families["source_evidence"]}
    records = []
    for item in families["provision_versions"]:
        logical = provisions[item["provision_id"]]
        version = versions[item["document_version_id"]]
        document = documents[version["document_id"]]
        context = []
        parent = logical.get("parent_provision_id")
        seen = {logical["provision_id"]}
        while parent:
            if parent in seen:
                raise ValueError("cyclic provision hierarchy")
            seen.add(parent)
            ancestor = provisions[parent]
            context.append(ancestor["label"] + " " + texts.get(parent, ""))
            parent = ancestor.get("parent_provision_id")
        anchor = item["source_anchor"]
        citation = Citation(
            source_artifact_id=anchor["source_artifact_id"],
            start_offset=anchor["start_offset"],
            end_offset=anchor["end_offset"],
            text=evidence[anchor["source_artifact_id"]][
                anchor["start_offset"] : anchor["end_offset"]
            ],
            document_id=version["document_id"],
            document_version_id=version["document_version_id"],
            provision_id=item["provision_id"],
            provision_version_id=item["provision_version_id"],
            canonical_path=tuple(logical["canonical_path"]),
        )
        parent_context = " ".join(context)
        records.append(
            ClauseRecord(
                citation,
                tokenize(
                    " ".join(
                        (
                            item["text"],
                            logical["label"],
                            parent_context,
                            document["title"],
                            document.get("official_number") or "",
                        )
                    )
                ),
                document["title"],
                parent_context,
            )
        )
    return tuple(sorted(records, key=lambda record: record.citation.provision_version_id))
