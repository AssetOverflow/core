# CORE Workbench API (W-026)

This package exposes the read-only local operator API for CORE Workbench v1.

Scope:

- runtime observability
- proposal visibility
- replay visibility
- eval visibility
- artifact visibility

The API is intentionally read-only by default.

Forbidden in W-026:

- proposal acceptance/rejection
- corpus mutation
- pack mutation
- workflow dispatch
- arbitrary shell execution
- arbitrary filesystem reads

Planned startup surfaces:

```bash
core workbench api
```

or:

```bash
python -m workbench.api
```

The API is local-first and should default to `127.0.0.1` only.
