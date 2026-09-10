"""Ranking actor-looks against a free-text description.

This is the whole product. Someone types who they want in their own words, and
the roster comes back ordered by how well each actor-look answers that.

Two scorers:

  ModelScorer   Gemini reads the description and each candidate's profile, and
                returns a fit score plus the phrases from the profile that
                justify it. This is the one that works.

  LexicalScorer Word overlap, used when no API key is configured. It is kept
                deliberately honest rather than propped up with a hand-written
                synonym table: the catalog and the query vocabulary are
                disjoint by construction, so overlap scoring genuinely cannot
                bridge "someone warm who explains things" to "unhurried,
                explains without condescending". It ranks by setting and
                literal words and says so. A padded fallback would hide exactly
                the gap the product exists to close.

`Match.evidence` is always quoted from the candidate's own profile text, so
"why is this person here" has a literal answer rather than a generated one.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..domain.models import Actor, Kind, Look, Query
from .llm import LLM, NullClient

#: Candidates per model call. Keeps one prompt well inside a comfortable
#: context while still giving the model a field wide enough to rank across.
BATCH = 60

#: Batches go out concurrently. They are independent — each scores its own
#: slice against the same query — and the calls are entirely latency-bound, so
#: running them in sequence turns a 20-second search into a minute of waiting
#: for no benefit.
#:
#: Kept low deliberately. Ten concurrent requests against a free-tier key
#: returned 429 on all ten, which does not fail loudly: every batch falls back
#: to word overlap and the screen silently gets worse. Slower and correct beats
#: faster and quietly degraded.
MAX_PARALLEL = 3

STOPWORDS = frozenset("""
a an and are as at be but by can for from has have he her his i in is it its me
my of on or our she that the their them they this to us was we who will with
you your want need looking someone somebody kind type actor person people find
should would could feel feels like really very quite some any bit anyone anything
""".split())


@dataclass(frozen=True, slots=True)
class Match:
    actor: Actor
    look: Look
    score: float
    evidence: tuple[str, ...]
    caveat: str | None
    source: str            # "model" | "lexical"

    @property
    def profile_text(self) -> str:
        return f"{self.actor.profile_text} {self.look.profile_text}"


def candidate_text(actor: Actor, look: Look) -> str:
    """The only thing a scorer ever sees. One place to change what is matchable."""
    return f"{actor.profile_text} Look: {look.profile_text}"


def _eligible(roster: list[Actor], query: Query) -> list[tuple[Actor, Look]]:
    """The type tabs the product already has. Not a constraint layer — the only
    thing that ever removes a candidate is the user asking for a narrower tab."""
    return [
        (actor, look)
        for actor in roster
        if query.kind is None or actor.kind is query.kind
        for look in actor.looks
    ]


# ------------------------------------------------------------------- model

SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "fit": {"type": "number"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "caveat": {"type": "string"},
                },
                "required": ["id", "fit"],
            },
        }
    },
    "required": ["results"],
}

PROMPT = """A casting user is looking for someone. In their words:

\"\"\"{query}\"\"\"

Below are performers on a roster, each with one specific look. The profiles are
written in a casting vocabulary that deliberately does not reuse the words a
request is written in, so judge on meaning, not on shared wording.

Return an entry for EVERY candidate listed, including the ones that do not fit.
An omitted candidate cannot be ranked, and a silently dropped performer is
indistinguishable from one you judged badly.

For each candidate return:
- id: the candidate's id, exactly as given.
- fit: 0.0-1.0, how well this performer in this look answers the request. Use
  the low end freely; most of a roster does not answer a specific request.
- evidence: up to three SHORT phrases copied verbatim from that candidate's own
  profile text that justify the score. Copy exactly; do not paraphrase. Return
  an empty list when nothing in the profile supports the request.
- caveat: at most one short clause naming what the request asks for that this
  candidate does not give. Omit it when there is nothing material.

Score the person and the look together. A performer whose read is right but
whose look is in the wrong setting is a partial match, not a full one.

Candidates:
{candidates}
"""


def _score_batch(pairs: list[tuple[Actor, Look]], query: Query,
                 client: LLM) -> dict[str, tuple[float, tuple[str, ...], str | None]]:
    listing = "\n".join(f"- {look.id}: {candidate_text(actor, look)}" for actor, look in pairs)
    payload = client.json(PROMPT.format(query=query.text.strip(), candidates=listing), SCHEMA)
    if not payload:
        return {}

    scored: dict[str, tuple[float, tuple[str, ...], str | None]] = {}
    known = {look.id: candidate_text(actor, look).lower() for actor, look in pairs}
    for row in payload.get("results", []):
        look_id, fit = row.get("id"), row.get("fit")
        if look_id not in known or not isinstance(fit, (int, float)):
            continue
        # Evidence must be quoted from the profile. A phrase the model wrote
        # itself is a claim about the record rather than a citation of it, and
        # those are the ones that turn out to be flattering and false.
        evidence = tuple(
            phrase.strip()
            for phrase in (row.get("evidence") or [])
            if isinstance(phrase, str) and phrase.strip().lower() in known[look_id]
        )[:3]
        caveat = row.get("caveat")
        scored[look_id] = (
            max(0.0, min(1.0, float(fit))),
            evidence,
            caveat.strip() if isinstance(caveat, str) and caveat.strip() else None,
        )
    return scored


# ----------------------------------------------------------------- lexical

def lexical_score(query: str, text: str) -> tuple[float, tuple[str, ...]]:
    """Word overlap. Weak on purpose — see the module docstring."""
    terms = {w for w in re.findall(r"[a-z]+", query.lower()) if w not in STOPWORDS and len(w) > 2}
    if not terms:
        return 0.0, ()
    haystack = text.lower()
    hit = tuple(sorted(t for t in terms if t in haystack))
    return len(hit) / len(terms), hit


# -------------------------------------------------------------------- entry

def search(roster: list[Actor], query: Query, client: LLM | None = None) -> list[Match]:
    """Rank every actor-look against the description. Never selects one."""
    client = client or NullClient()
    pairs = _eligible(roster, query)
    if query.is_empty:
        return []

    scored: dict[str, tuple[float, tuple[str, ...], str | None]] = {}
    complete = False
    if client.available:
        batches = [pairs[start:start + BATCH] for start in range(0, len(pairs), BATCH)]
        if len(batches) == 1:
            scored = _score_batch(batches[0], query, client)
        else:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(batches))) as pool:
                for result in pool.map(lambda b: _score_batch(b, query, client), batches):
                    scored.update(result)
        # Every candidate has to come back scored, or the model path is not
        # usable for this search. A partial response would leave some entries
        # scored by the model and the rest by word overlap, and those are
        # different scales — a 0.95 judgement ranked against a 0.20 word count
        # is a list sorted by two incompatible numbers.
        complete = len(scored) == len(pairs)

    matches = []
    for actor, look in pairs:
        if complete:
            fit, evidence, caveat = scored[look.id]
            source = "model"
        else:
            fit, evidence = lexical_score(query.text, candidate_text(actor, look))
            caveat, source = None, "lexical"
        matches.append(
            Match(actor=actor, look=look, score=round(fit, 6),
                  evidence=evidence, caveat=caveat, source=source)
        )

    # Ties break on ids so the order is stable across runs and a genuine
    # reordering is a signal rather than dictionary churn.
    matches.sort(key=lambda m: (-m.score, m.actor.id, m.look.id))
    return [m for m in matches if m.score > 0][: query.limit]
