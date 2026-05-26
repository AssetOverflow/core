"""CORE Workbench read-only API surface.

ADR-0160 / W-026.

This API intentionally exposes a narrow local-first operator surface and does
not provide proposal/corpus mutation endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from workbench.readers import (
    list_artifacts,
    list_eval_lanes,
    list_proposals,
    read_artifact,
    read_proposal,
    replay_artifact,
    run_safe_eval_lane,
    runtime_status,
)
from workbench.schemas import error, ok


class EvalRunRequest(BaseModel):
    lane: str
    version: str = "v1"
    split: str = "public"


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

    @app.get("/proposals")
    def proposals() -> JSONResponse:
        return JSONResponse(ok({"items": list_proposals()}))

    @app.get("/proposals/{proposal_id}")
    def proposal_detail(proposal_id: str) -> JSONResponse:
        try:
            proposal = read_proposal(proposal_id)
        except FileNotFoundError:
            return JSONResponse(
                error("not_found", f"proposal not found: {proposal_id}"),
                status_code=404,
            )
        return JSONResponse(ok(proposal))

    @app.get("/evals")
    def evals() -> JSONResponse:
        return JSONResponse(ok({"lanes": list_eval_lanes()}))

    @app.post("/evals/run")
    def eval_run(request: EvalRunRequest) -> JSONResponse:
        try:
            result = run_safe_eval_lane(
                request.lane,
                version=request.version,
                split=request.split,
            )
        except ValueError as exc:
            return JSONResponse(
                error("bad_request", str(exc)),
                status_code=400,
            )
        except FileNotFoundError as exc:
            return JSONResponse(
                error("not_found", str(exc)),
                status_code=404,
            )
        return JSONResponse(ok(result))

    @app.get("/replay/{artifact_id:path}")
    def replay(artifact_id: str) -> JSONResponse:
        try:
            comparison = replay_artifact(artifact_id)
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
        return JSONResponse(ok(comparison))

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
