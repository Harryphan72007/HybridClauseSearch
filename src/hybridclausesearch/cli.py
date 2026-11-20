"""hcs command-line interface (Typer)."""

from __future__ import annotations

import json
import platform
from datetime import date
from pathlib import Path

import typer

from hybridclausesearch import __version__
from hybridclausesearch.bm25 import BM25Index
from hybridclausesearch.config import load_settings
from hybridclausesearch.contracts import SearchRequest
from hybridclausesearch.logging import configure_logging
from hybridclausesearch.snapshot import load_snapshot
from hybridclausesearch.storage import load_index, save_index

app = typer.Typer(add_completion=False, help="HybridClauseSearch CLI.")


@app.command("index")
def index_command(
    snapshot_dir: Path,
    index_path: Path,
    expected_sha256: str = typer.Option(..., "--expected-sha256"),
    synthetic_development: bool = typer.Option(False, "--synthetic-development"),
) -> None:
    """Build an index from a pinned, validated CorpusSnapshot."""
    try:
        snapshot = load_snapshot(
            snapshot_dir, expected_sha256=expected_sha256, require_ready=not synthetic_development
        )
        index = BM25Index(snapshot)
        save_index(index, index_path)
        typer.echo(
            json.dumps(
                {
                    "snapshot_sha256": snapshot.digest,
                    "index_path": str(index_path),
                    "record_count": len(index.records),
                    "source_review_ready": snapshot.ready,
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError, KeyError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("search")
def search_command(
    snapshot_dir: Path,
    index_path: Path,
    query: str,
    expected_sha256: str = typer.Option(..., "--expected-sha256"),
    review_date: str = typer.Option(..., "--review-date"),
    query_id: str = typer.Option("query:cli", "--query-id"),
    limit: int = typer.Option(10, "--limit", min=1),
    document_id: str = typer.Option("", "--document-ids", help="Comma-separated document IDs"),
    include_unknown: bool = typer.Option(True, "--include-unknown/--exclude-unknown"),
    synthetic_development: bool = typer.Option(False, "--synthetic-development"),
) -> None:
    """Return ranked clauses and exact citations as structured JSON."""
    try:
        snapshot = load_snapshot(
            snapshot_dir, expected_sha256=expected_sha256, require_ready=not synthetic_development
        )
        request = SearchRequest(
            query_id=query_id,
            query=query,
            snapshot_sha256=expected_sha256,
            review_date=date.fromisoformat(review_date),
            limit=limit,
            document_ids=tuple(
                identifier.strip() for identifier in document_id.split(",") if identifier.strip()
            ),
            include_unknown=include_unknown,
        )
        results = load_index(index_path, snapshot).search(request)
        typer.echo(
            json.dumps(
                {
                    "query_id": request.query_id,
                    "snapshot_sha256": snapshot.digest,
                    "source_review_ready": snapshot.ready,
                    "results": [hit.model_dump(mode="json") for hit in results],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, KeyError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Report the runtime environment and check that data directories are writable."""
    settings = load_settings()
    configure_logging(settings.log_level)
    typer.echo(f"package:  hybridclausesearch {__version__}")
    typer.echo(f"python:   {platform.python_version()} ({platform.platform()})")
    typer.echo(f"data_dir: {settings.data_dir.resolve()}")
    for label, path in (
        ("raw", settings.raw_dir),
        ("processed", settings.processed_dir),
        ("samples", settings.samples_dir),
        ("out", settings.out_dir),
    ):
        status = "ok" if _check_writable(path) else "NOT writable"
        typer.echo(f"  {label:<10} {path} -> {status}")


def _check_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


if __name__ == "__main__":
    app()
