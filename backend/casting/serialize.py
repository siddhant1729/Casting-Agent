"""Record -> JSON. Kept apart from the pipeline so the shapes the UI depends on
are visible in one file and cannot drift by accident.
"""

from __future__ import annotations

from typing import Any

from .domain.models import Actor, Look, Query
from .pipeline import ResultItem, Results
from .reasoning.explain import Rationale, Reservation
from .reasoning.search import Match


def look_json(look: Look) -> dict[str, Any]:
    return {
        "id": look.id,
        "setting": look.setting.value,
        "scene": look.scene,
        "wardrobe": look.wardrobe,
        "framing": list(look.framing),
    }


def actor_json(actor: Actor) -> dict[str, Any]:
    return {
        "id": actor.id,
        "name": actor.name,
        "kind": actor.kind.value,
        "age_band": actor.age_band,
        "presents_as": actor.presents_as,
        "languages": {code: level.value for code, level in actor.languages.items()},
        "language_text": actor.language_text,
        "appearance": actor.appearance,
        "delivery": actor.delivery,
        "voice": list(actor.voice),
        "look_count": len(actor.looks),
        "settings": [look.setting.value for look in actor.looks],
        # Deterministic per actor, used to draw abstract geometry in the
        # browser. No photoreal face is generated anywhere.
        "portrait_seed": sum(ord(c) for c in actor.id + actor.name),
        "planted": actor.planted,
    }


def match_json(match: Match) -> dict[str, Any]:
    return {
        "score": round(match.score, 4),
        "evidence": list(match.evidence),
        "source": match.source,
    }


def rationale_json(text: Rationale) -> dict[str, Any]:
    return {
        "text": text.text,
        "sentences": [{"text": s.text, "cites": list(s.cites)} for s in text.sentences],
        "cites": list(text.cites),
    }


def reservation_json(item: Reservation) -> dict[str, Any]:
    return {"kind": item.kind.value, "text": item.text, "cites": list(item.cites)}


def item_json(item: ResultItem) -> dict[str, Any]:
    return {
        "rank": item.rank,
        "actor": actor_json(item.match.actor),
        "look": look_json(item.match.look),
        "match": match_json(item.match),
        "rationale": rationale_json(item.rationale),
        "reservation": reservation_json(item.reservation),
    }


def query_json(query: Query) -> dict[str, Any]:
    return {
        "text": query.text,
        "kind": query.kind.value if query.kind else None,
        "limit": query.limit,
    }


def results_json(results: Results) -> dict[str, Any]:
    return {
        "query": query_json(results.query),
        "items": [item_json(i) for i in results.items],
        "seed": results.seed,
        "roster_size": results.roster_size,
        "look_count": results.look_count,
        "scorer": results.scorer,
        "model_used": results.model_used,
        "returned": len(results.items),
    }
