"""CORE Workbench read-only API surface.

ADR-0160 / W-026.

This API intentionally exposes a narrow local-first operator surface and does
not provide proposal/corpus mutation endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from workbench.readers import list_artifacts, read_artifact, runtime_status
from workbench.schemas import error, ok


def create_app() -> FastAPI:
    app = FastAPI(
        title="CORE Workbench API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(ok({"status": "ok"}))

    @app.get("/runtime/status")
    def runtime() -> JSONResponse:
        return JSONResponse(ok(runtime_status()))

    @app.get("/artifacts")
    def artifacts(limit: int = 100) -> JSONResponse:
        return JSONResponse(ok({"items": list_artifacts(limit=limit)}))

    @app.get("/artifacts/{artifact_id:path}")
    def artifact_detail(artifact_id: str) -> JSONResponse:
        try:
            artifact = read_artifact(artifact_id)
        except FileNotFoundError:
            return JSONResponse(
                error("not_found", f"artifact not found: {artifact_id}"),
                status_code=404,
            )
        except ValueError as exc:
            return JSONResponse(
                error("bad_request", str(exc)),
                status_code=400,
            )
        return JSONResponse(ok(artifact))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "workbench.api:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )
