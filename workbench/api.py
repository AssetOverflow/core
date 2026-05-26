"""CORE Workbench read-only API surface.

ADR-0160 / W-026.

This API intentionally exposes a narrow local-first operator surface and does
not provide proposal/corpus mutation endpoints.
"""

from __future__ import annotations

from fastapi import Cookie, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from workbench.auth import authenticate, load_auth_config, verify_session_token
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

_SESSION_COOKIE = "core_workbench_session"


class LoginRequest(BaseModel):
    email: str
    password: str


class EvalRunRequest(BaseModel):
    lane: str
    version: str = "v1"
    split: str = "public"


def _auth_required(session: str | None = Cookie(default=None, alias=_SESSION_COOKIE)) -> str:
    cfg = load_auth_config()
    if not cfg.configured:
        raise PermissionError("workbench auth is not configured")
    payload = verify_session_token(session or "", cfg.session_secret)
    if payload is None or payload.get("email") != cfg.admin_email:
        raise PermissionError("authentication required")
    return str(payload["email"])


def _auth_error(message: str) -> JSONResponse:
    return JSONResponse(error("unauthorized", message), status_code=401)


def create_app() -> FastAPI:
    app = FastAPI(
        title="CORE Workbench API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @app.exception_handler(PermissionError)
    def permission_error_handler(_request: Request, exc: PermissionError) -> JSONResponse:
        return _auth_error(str(exc))

    @app.get("/health")
    def health() -> JSONResponse:
        cfg = load_auth_config()
        return JSONResponse(ok({"status": "ok", "auth_configured": cfg.configured}))

    @app.post("/auth/login")
    def login(request: LoginRequest) -> JSONResponse:
        token = authenticate(request.email, request.password)
        if token is None:
            return _auth_error("invalid credentials")
        response = JSONResponse(ok({"email": request.email}))
        response.set_cookie(
            _SESSION_COOKIE,
            token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 8,
        )
        return response

    @app.post("/auth/logout")
    def logout(_email: str = Depends(_auth_required)) -> JSONResponse:
        response = JSONResponse(ok({"logged_out": True}))
        response.delete_cookie(_SESSION_COOKIE)
        return response

    @app.get("/auth/me")
    def me(email: str = Depends(_auth_required)) -> JSONResponse:
        return JSONResponse(ok({"email": email}))

    @app.get("/runtime/status")
    def runtime(_email: str = Depends(_auth_required)) -> JSONResponse:
        return JSONResponse(ok(runtime_status()))

    @app.get("/artifacts")
    def artifacts(limit: int = 100, _email: str = Depends(_auth_required)) -> JSONResponse:
        return JSONResponse(ok({"items": list_artifacts(limit=limit)}))

    @app.get("/artifacts/{artifact_id:path}")
    def artifact_detail(artifact_id: str, _email: str = Depends(_auth_required)) -> JSONResponse:
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
    def proposals(_email: str = Depends(_auth_required)) -> JSONResponse:
        return JSONResponse(ok({"items": list_proposals()}))

    @app.get("/proposals/{proposal_id}")
    def proposal_detail(proposal_id: str, _email: str = Depends(_auth_required)) -> JSONResponse:
        try:
            proposal = read_proposal(proposal_id)
        except FileNotFoundError:
            return JSONResponse(
                error("not_found", f"proposal not found: {proposal_id}"),
                status_code=404,
            )
        return JSONResponse(ok(proposal))

    @app.get("/evals")
    def evals(_email: str = Depends(_auth_required)) -> JSONResponse:
        return JSONResponse(ok({"lanes": list_eval_lanes()}))

    @app.post("/evals/run")
    def eval_run(request: EvalRunRequest, _email: str = Depends(_auth_required)) -> JSONResponse:
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
    def replay(artifact_id: str, _email: str = Depends(_auth_required)) -> JSONResponse:
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
