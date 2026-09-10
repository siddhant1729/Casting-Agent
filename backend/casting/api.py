"""HTTP surface. Thin on purpose — every decision it exposes is made and tested
in `casting/`, and this file only maps requests onto it.

    .venv/bin/uvicorn casting.api:app --reload
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import env
from .domain.catalog import build_roster, search_by_name
from .domain.models import Kind, Query, Setting
from .pipeline import (
    DEFAULT_LIMIT,
    DEFAULT_SEED,
    EXAMPLE_QUERIES,
    empty_results,
    route,
    run,
)
from .reasoning.llm import get_client
from .serialize import actor_json, results_json

# On Render nothing sources a shell profile before uvicorn starts, and the
# dashboard's environment variables are already in os.environ by then. Loading
# here is a no-op in that case (the real environment always wins) and is what
# makes a local `uvicorn casting.api:app` see .env without run.sh.
env.load()

app = FastAPI(title="Casting Agent", version="0.2.0")

# Any localhost port, not just 5173.
#
# Vite silently falls back to 5174 when 5173 is taken — by a stray dev server,
# another project, anything. A fixed allowlist turns that into a browser CORS
# block, which surfaces in the UI as "backend unreachable" while the API is in
# fact running and healthy. The port a dev server happens to land on is not a
# security boundary; the loopback interface is.
#
# In a deployment the browser origin is not loopback at all, so ALLOWED_ORIGINS
# (comma-separated) carries the frontend's URL. Render static sites and web
# services both land on *.onrender.com, which the regex covers so a preview
# deploy with a generated hostname is not a CORS mystery.
LOCAL_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"
RENDER_ORIGIN_REGEX = r"https://[a-z0-9-]+\.onrender\.com"


def allowed_origins() -> list[str]:
    """Explicit extra origins from the environment, blanks and slashes trimmed."""
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_origin_regex=f"{LOCAL_ORIGIN_REGEX}|{RENDER_ORIGIN_REGEX}",
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = ""
    kind: str | None = None          # None = the "All" tab
    seed: int = DEFAULT_SEED
    limit: int = Field(DEFAULT_LIMIT, ge=1, le=100)


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    """What the UI needs to render honestly."""
    # The roster the default seed builds, so the screen can say how much work a
    # search is doing while it is doing it. A search takes eight to eleven
    # seconds, and "reading 138 look profiles" is the difference between a wait
    # and a hang. Same seed the UI searches with, so the number is the real one.
    roster = build_roster(DEFAULT_SEED)
    return {
        "examples": list(EXAMPLE_QUERIES),
        "default_seed": DEFAULT_SEED,
        "roster_size": len(roster),
        "look_count": sum(len(actor.looks) for actor in roster),
        "model_available": get_client().available,
        "catalog_notice": (
            "Synthetic catalog. Actors and looks are generated from the seed shown. "
            "No real person is represented."
        ),
        "scorer_notice": (
            "Without an API key, ranking falls back to word overlap. The catalog is "
            "written in a vocabulary that shares no words with a typed request, so the "
            "fallback ranks on literal terms only and will miss the point."
        ),
        "kinds": [k.value for k in Kind],
        "settings": [s.value for s in Setting],
    }


def _kind(value: str | None) -> Kind | None:
    """Unknown values fall back to the All tab rather than erroring."""
    return Kind(value) if value in {k.value for k in Kind} else None


@app.post("/api/search")
def search_endpoint(request: SearchRequest) -> dict[str, Any]:
    """One box, both searches, routed here.

    A name off the roster and a description of a person arrive through the same
    input, and the server decides which search answers. The browser renders what
    comes back and the label that says where it came from; it does not choose a
    path, and it does not re-score or re-sort anything.

    A query that is both — a name plus some description of what they are doing —
    runs both, and the response carries both lists.
    """
    query = Query(text=request.query, kind=_kind(request.kind), limit=request.limit)
    plan = route(request.query, build_roster(request.seed))

    # The name half is the roster's own search, reached through the endpoint that
    # already exposes it rather than through a second copy of the matching rule.
    # `route` guarantees a non-blank term here, so the blank-term case (which
    # returns the whole grid) cannot be reached by accident.
    names = [
        actors_endpoint(request.model_copy(update={"query": term}))
        for term in plan.name_terms
    ]
    seen: set[str] = set()
    matched_actors = [
        actor
        for body in names
        for actor in body["actors"]
        if not (actor["id"] in seen or seen.add(actor["id"]))
    ]

    ranked = (
        run(query, seed=request.seed, client=get_client())
        if plan.wants_ranking
        else empty_results(query, seed=request.seed)
    )
    return {
        **results_json(ranked),
        # What ran: "name", "description", "both", or "empty". The UI says so in
        # plain language rather than inferring it from which list is longer.
        "route": plan.label,
        "actors": matched_actors[: request.limit],
        "matched_names": len(matched_actors),
    }


@app.post("/api/actors")
def actors_endpoint(request: SearchRequest) -> dict[str, Any]:
    """The roster's existing name search, over the same catalog.

    Exists so the comparison view has a real left-hand panel rather than a
    staged empty state. A description typed into a name search returns nothing
    because no performer is called "warm, credible, explains money without
    sounding like a bank" — that is the honest result, and it is the point.
    """
    kind = _kind(request.kind)
    roster = build_roster(request.seed)
    matched = [
        actor for actor in search_by_name(roster, request.query)
        if kind is None or actor.kind is kind
    ]
    return {
        "query": {"text": request.query, "kind": kind.value if kind else None},
        "actors": [actor_json(actor) for actor in matched[: request.limit]],
        "matched": len(matched),
        "roster_size": len(roster),
        "seed": request.seed,
        # Named so the UI never has to infer why the panel is empty.
        "search_field": "name",
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Whether a model is configured, and why the last call failed if it did.

    Reports the *reason*, never the key or the model's response. A silent
    degrade is right for the user and useless for whoever has to work out why
    the ranking got worse.
    """
    client = get_client()
    return {
        "ok": True,
        "model_available": client.available,
        "last_error": client.last_error,
    }


# --- Optional single-service mode -------------------------------------------
#
# Two shapes deploy from this file. Two Render services (a static site for the
# frontend, this as the API) is the default and needs nothing below. One service
# that serves both is cheaper and has no cross-origin surface at all; it happens
# whenever a built `frontend/dist` is present, so the same image works either
# way and an unbuilt checkout stays a pure API rather than 404-ing on itself.

def find_frontend_dist() -> Path | None:
    """`frontend/dist` relative to the repo root, if it has been built."""
    override = os.environ.get("FRONTEND_DIST")
    candidates = [Path(override)] if override else [
        parent / "frontend" / "dist" for parent in Path(__file__).resolve().parents[:4]
    ]
    return next((c for c in candidates if (c / "index.html").is_file()), None)


FRONTEND_DIST = find_frontend_dist()

if FRONTEND_DIST is not None:
    # Hashed build assets. Mounted before the catch-all so a missing asset is a
    # 404 rather than index.html served with a JavaScript content type.
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        """Serve the built file when it exists, else index.html.

        The router is client-side, so /compare is a real URL to the user and a
        nonexistent file to the server. Returning index.html is what makes a
        reload or a shared link land on the page instead of a 404. The /api
        routes are declared above and match first.
        """
        candidate = (FRONTEND_DIST / path).resolve()
        if path and FRONTEND_DIST in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
