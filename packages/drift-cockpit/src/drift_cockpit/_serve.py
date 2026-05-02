"""FastAPI application that serves the static cockpit frontend and proxies /api/cockpit/* calls.

Usage (via `drift cockpit serve`):
    drift cockpit serve --port 8000 --api-url http://localhost:8001
"""
from __future__ import annotations

import importlib.resources
import re
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

_STATIC_PACKAGE = "drift_cockpit.static"
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._~-]+$")
_ALLOWED_SCHEMES = {"http", "https"}


def _parse_api_url(api_url: str) -> tuple[str, str]:
    """Parse and validate api_url, returning (scheme, netloc).

    Raises ValueError if the URL is not a valid http/https URL.
    """
    parsed = urlparse(api_url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"api_url scheme must be http or https, got: {parsed.scheme!r}"
        )
    if not parsed.netloc:
        raise ValueError(f"api_url must include a host, got: {api_url!r}")
    return parsed.scheme, parsed.netloc


def _locate_static_dir() -> Path | None:
    """Return the Path to the bundled static/ directory, or None if empty/missing."""
    try:
        ref = importlib.resources.files(_STATIC_PACKAGE)
        candidate = Path(str(ref))
        # The directory must contain at least one non-infrastructure file to be usable.
        _skip = {".gitkeep", "__init__.py", "__pycache__"}
        if candidate.is_dir() and any(
            f for f in candidate.iterdir() if f.name not in _skip
        ):
            return candidate
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    return None


def create_app(api_url: str) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        api_url: Base URL of the Drift Cockpit backend API (e.g. http://localhost:8001).
    """
    # Parse api_url once at startup so scheme+netloc are trusted constants,
    # never re-derived from per-request user input (prevents SSRF).
    _api_scheme, _api_netloc = _parse_api_url(api_url)

    app = FastAPI(title="Drift Cockpit", docs_url=None, redoc_url=None)

    static_dir = _locate_static_dir()

    # ------------------------------------------------------------------
    # Proxy: /api/cockpit/* -> backend api_url/api/cockpit/*
    # ------------------------------------------------------------------
    @app.api_route(
        "/api/cockpit/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def proxy_api(request: Request, path: str) -> Response:
        # Reject path forms that can be interpreted as absolute/external targets.
        if (
            not path
            or path.startswith(("/", "\\"))
            or "://" in path
            or path.startswith("//")
        ):
            return JSONResponse({"error": "invalid proxy path"}, status_code=400)

        segments = path.split("/")
        if any(
            not seg
            or seg in {".", ".."}
            or any(c in seg for c in ("/", "\\", "?", "#", "%"))
            or _PATH_SEGMENT_RE.fullmatch(seg) is None
            for seg in segments
        ):
            return JSONResponse({"error": "invalid proxy path"}, status_code=400)

        safe_path = "/api/cockpit/" + "/".join(quote(seg, safe="-_.~") for seg in segments)

        query = ""
        if request.query_string:
            # Parse and re-encode to prevent query-string injection into the URL
            pairs = parse_qsl(
                request.query_string.decode(errors="replace"),
                keep_blank_values=True,
            )
            query = urlencode(pairs)

        # Reconstruct the target URL entirely from trusted components:
        # scheme and netloc come from the startup-validated api_url constant,
        # so the host is never influenced by the incoming request.
        target = urlunparse((_api_scheme, _api_netloc, safe_path, "", query, ""))

        body = await request.body()
        async with httpx.AsyncClient() as client:
            upstream = await client.request(
                method=request.method,
                url=target,
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() not in ("host", "content-length")
                },
                content=body,
            )
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=dict(upstream.headers),
        )

    # ------------------------------------------------------------------
    # Static assets (Next.js static export)
    # ------------------------------------------------------------------
    if static_dir is not None:
        app.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="static",
        )
    else:

        @app.get("/")
        async def no_frontend() -> JSONResponse:  # drift:ignore[MAZ]
            return JSONResponse(
                {
                    "error": "No frontend assets found.",
                    "hint": (
                        "Run `make cockpit-build` to build the Next.js app and copy "
                        "the output to packages/drift-cockpit/src/drift_cockpit/static/."
                    ),
                },
                status_code=503,
            )

    return app
