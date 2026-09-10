"""Description in, ranked actor-looks out.

    query ─▶ search ─▶ explain ─▶ results
             (LLM)     (pure)

Short by design. There is no constraint solver and no cost model any more:
usage is covered by membership, so the only question left is who answers the
description, and that is one stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain.catalog import build_roster
from .domain.models import Kind, Query
from .reasoning.explain import Rationale, Reservation, rationale, reservation
from .reasoning.llm import LLM, NullClient
from .reasoning.search import Match, search

DEFAULT_SEED = 7
DEFAULT_LIMIT = 24

#: The first screen is never empty. Each one exercises a different path:
#: the first is pure delivery with no setting cue, the second names a room, the
#: third asks for something the roster answers only partially.
EXAMPLE_QUERIES = (
    {
        "label": "Warm explainer",
        "text": "Someone warm and credible who can explain a money app without "
                "talking down to anyone. Should feel like a person you'd actually ask.",
    },
    {
        "label": "Teacher, on camera",
        "text": "A teacher type at a whiteboard — patient, authoritative, comfortable "
                "with a class in front of them. Hindi and Tamil.",
    },
    {
        "label": "High-energy, outdoors",
        "text": "Young, fast-talking, a bit irreverent. Outdoors or on the street, "
                "handheld, nothing studio-lit.",
    },
)


@dataclass(frozen=True, slots=True)
class ResultItem:
    rank: int
    match: Match
    rationale: Rationale
    reservation: Reservation


@dataclass(frozen=True, slots=True)
class Results:
    query: Query
    items: tuple[ResultItem, ...]
    seed: int
    roster_size: int
    look_count: int
    #: "model" or "lexical". A ranking produced by word overlap is a different
    #: artefact from one a model produced, and the UI says which it is showing.
    scorer: str

    @property
    def model_used(self) -> bool:
        return self.scorer == "model"


def run(query: Query, *, seed: int = DEFAULT_SEED, client: LLM | None = None) -> Results:
    client = client or NullClient()
    roster = build_roster(seed)
    matches = search(roster, query, client)

    items = tuple(
        ResultItem(
            rank=position,
            match=match,
            rationale=rationale(match),
            reservation=reservation(match, query),
        )
        for position, match in enumerate(matches, start=1)
    )
    return Results(
        query=query,
        items=items,
        seed=seed,
        roster_size=len(roster),
        look_count=sum(len(a.looks) for a in roster),
        scorer="model" if any(m.source == "model" for m in matches) else "lexical",
    )


def from_text(text: str, *, kind: Kind | None = None, seed: int = DEFAULT_SEED,
              limit: int = DEFAULT_LIMIT, client: LLM | None = None) -> Results:
    return run(Query(text=text, kind=kind, limit=limit), seed=seed, client=client)
