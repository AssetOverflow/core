"""Standalone startup entrypoint for CORE Workbench API."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("CORE_WORKBENCH_HOST", "127.0.0.1")
    port_raw = os.environ.get("CORE_WORKBENCH_PORT", "8765")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise SystemExit(f"invalid CORE_WORKBENCH_PORT: {port_raw!r}") from exc

    uvicorn.run(
        "workbench.api:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
