"""HTTP surface. Thin on purpose — every decision it exposes is made and tested
in `casting/`, and this file only maps requests onto it.

    .venv/bin/uvicorn casting.api:app --reload
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .domain.catalog import build_roster, search_by_name
from .domain.models import Kind, Query, Setting
from .pipeline import DEFAULT_LIMIT, DEFAULT_SEED, EXAMPLE_QUERIES, run
from .reasoning.llm import get_client
from .serialize import actor_json, results_json

app = FastAPI(title="Casting Agent", version="0.2.0")
# Any localhost port, not just 5173.
#
# Vite silently falls back to 5174 when 5173 is taken — by a stray dev server,
# another project, anything. A fixed allowlist turns that into a browser CORS
# block, which surfaces in the UI as "backend unreachable" while the API is in
# fact running and healthy. The port a dev server happens to land on is not a
# security boundary; the loopback interface is.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
    return {
        "examples": list(EXAMPLE_QUERIES),
        "default_seed": DEFAULT_SEED,
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
    query = Query(text=request.query, kind=_kind(request.kind), limit=request.limit)
    return results_json(run(query, seed=request.seed, client=get_client()))


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
