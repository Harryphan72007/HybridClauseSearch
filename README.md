# HybridClauseSearch

Hybrid lexical + dense retrieval over Vietnamese legal clauses.

> Status: **development (v0.1.0)**. Lexical retrieval is an engineering baseline;
> synthetic examples do not establish legal coverage or retrieval quality.

## Quickstart

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Unix: source .venv/bin/activate
pip install -e ".[dev]"

hcs version      # -> 0.1.0
hcs doctor       # environment + writable data dirs
```

`hcs index SNAPSHOT_DIR INDEX_JSON --expected-sha256 TRUSTED_DIGEST` validates
the corpus and requires completed G1 source review. `hcs search SNAPSHOT_DIR
INDEX_JSON "query" --expected-sha256 TRUSTED_DIGEST --review-date YYYY-MM-DD`
returns JSON with exact source spans, version IDs, scores and applicability state.
The digest must be obtained independently from the snapshot package. Install
VietLegalCorpus in the same environment for full production schema and quality
validation. Use
`--synthetic-development` only for clearly identified unreviewed fixtures.
Unknown applicability is returned explicitly unless `--exclude-unknown` is used.

For a cross-repository synthetic smoke test, install VietLegalCorpus and this
package in the same environment, then run:

```bash
python examples/synthetic_demo.py ../VietLegalCorpus out/synthetic-demo
```

The output contains a validated snapshot, persisted index and `demo.json`.
It does not contain reviewed relevance judgments or real-law benchmark results.

## Tasks

`make` is the canonical runner (used in CI). Equivalent direct commands:

| Task | make | direct |
|---|---|---|
| tests | `make test` | `python -m pytest -q` |
| lint | `make lint` | `python -m ruff check src tests` |
| typecheck | `make typecheck` | `python -m mypy src` |
| gate | `make check` | run the three above |
| demo | `make demo` | `python -m hybridclausesearch.cli doctor` |

## Layout

```
src/hybridclausesearch/   package (cli, config, logging, schemas/)
tests/            unit / fixtures / golden
data/             raw (gitignored) · samples (committed) · processed (gitignored)
```

## License

Licensed under the [Apache License 2.0](LICENSE), matching the package metadata.
