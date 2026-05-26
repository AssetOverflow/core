"""Standalone startup entrypoint for CORE Workbench API."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "workbench.api:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
