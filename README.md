# HybridClauseSearch

Hybrid lexical + dense retrieval over Vietnamese legal clauses.

> Status: **scaffold (v0.1.0)** — walking skeleton only. Feature PRs land per the implementation plan.

## Quickstart

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Unix: source .venv/bin/activate
pip install -e ".[dev]"

hcs version      # -> 0.1.0
hcs doctor       # environment + writable data dirs
```

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
