"""Description in, ranked actor-looks out.

    query ─▶ search ─▶ explain ─▶ results
             (LLM)     (pure)

Short by design. There is no constraint solver and no cost model any more:
usage is covered by membership, so the only question left is who answers the
description, and that is one stage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .domain.catalog import build_roster, search_by_name
from .domain.models import Actor, Kind, Query
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


# --- Routing -----------------------------------------------------------------
#
# One box takes both kinds of query: a name off the roster ("Rohan", "Arjun B.")
# and a description of a person ("warm, credible, explains money without talking
# down to anyone"). Which search runs is decided here, on the server. The browser
# is handed the answer and the label for it, and never chooses.
#
# Matching itself is not reimplemented — the name half is the roster's own
# `search_by_name`, reached through the existing endpoint. What lives here is the
# narrower question of whether a typed word is *meant* as a name at all.

#: Below this a word is too short to route on. It keeps initials ("B.") from
#: dragging in every actor who happens to share one.
MIN_NAME_WORD = 3


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= MIN_NAME_WORD]


def name_words(roster: list[Actor]) -> set[str]:
    """The roster's names, split into whole words.

    Whole words, not substrings, and this is the reason: `search_by_name` is a
    substring match, so "man" reaches Manav and "ash" reaches Aakash. Routing on
    that would send "a man who explains things" down the name path on the
    strength of an article. A word is treated as a name only when it *is* one of
    the words in a name.
    """
    return {
        word
        for actor in roster
        for word in _words(actor.name)
    }


@dataclass(frozen=True, slots=True)
class Route:
    """Which searches a query asks for, and the words that decided it."""
    name_terms: tuple[str, ...]
    description: str

    @property
    def wants_names(self) -> bool:
        return bool(self.name_terms)

    @property
    def wants_ranking(self) -> bool:
        return bool(self.description)

    @property
    def label(self) -> str:
        if self.wants_names and self.wants_ranking:
            return "both"
        if self.wants_names:
            return "name"
        return "description" if self.wants_ranking else "empty"


#: A residue this short is not a description. "Arjun B." leaves nothing behind;
#: "Rohan at a whiteboard, patient" leaves enough to rank on.
MIN_DESCRIPTION_WORDS = 2


def route(text: str, roster: list[Actor]) -> Route:
    """Split a typed query into the name half and the descriptive half.

    A blank query asks for neither. The whole string is tried as a name first, so
    "Arjun B." routes on the name a user actually typed rather than on the token
    it splits into.
    """
    typed = text.strip()
    if not typed:
        return Route(name_terms=(), description="")

    known = name_words(roster)
    if search_by_name(roster, typed):
        terms, leftover = (typed,), []
    else:
        words = _words(typed)
        terms = tuple(w for w in words if w in known)
        leftover = [w for w in words if w not in known]

    described = typed if not terms else (
        typed if len(leftover) >= MIN_DESCRIPTION_WORDS else ""
    )
    return Route(name_terms=terms, description=described)


def empty_results(query: Query, *, seed: int = DEFAULT_SEED) -> Results:
    """The shape of a search that never ran a scorer.

    A pure name lookup ranks nothing, so there is no scorer to name and no model
    call to make. The screen still needs the roster counts and the seed.
    """
    roster = build_roster(seed)
    return Results(
        query=query,
        items=(),
        seed=seed,
        roster_size=len(roster),
        look_count=sum(len(a.looks) for a in roster),
        scorer="none",
    )
