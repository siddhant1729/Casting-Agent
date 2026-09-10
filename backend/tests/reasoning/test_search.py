"""Ranking actor-looks against a description. The core of the product."""

from __future__ import annotations

import pytest

from casting.domain.catalog import build_roster
from casting.domain.models import Kind, Query, Setting
from casting.reasoning.search import (
    BATCH,
    Match,
    candidate_text,
    lexical_score,
    search,
)


@pytest.fixture
def roster():
    return build_roster(7)


class StubClient:
    """Not a mock of Gemini — a way to drive the scoring and validation paths.

    Scores every candidate in the prompt, because a partial response is no
    longer usable (see `test_a_partial_model_response_falls_back_entirely`).
    `overrides` replaces the entry for specific ids.
    """
    available = True

    def __init__(self, overrides=None, payload=None, default_fit=0.4, drop=()):
        self.overrides = {row["id"]: row for row in (overrides or [])}
        self.payload = payload
        self.default_fit = default_fit
        self.drop = set(drop)
        self.calls = 0
        self.prompts: list[str] = []

    def json(self, prompt, schema):
        self.calls += 1
        self.prompts.append(prompt)
        if self.payload is not None:
            return self.payload
        ids = [
            line.split(":")[0].strip("- ")
            for line in prompt.splitlines() if line.startswith("- ")
        ]
        return {
            "results": [
                self.overrides.get(i, {"id": i, "fit": self.default_fit, "evidence": []})
                for i in ids if i not in self.drop
            ]
        }


# ------------------------------------------------------------------- shape

def test_ranking_is_at_look_level(roster):
    query = Query("someone in a kitchen", limit=200)
    matches = search(roster, query)
    assert all(isinstance(m, Match) for m in matches)
    assert len({m.look.id for m in matches}) == len(matches)


def test_one_actor_can_appear_more_than_once_with_different_looks(roster):
    matches = search(roster, Query("hindi", limit=200))
    seen = [m.actor.id for m in matches]
    assert len(seen) != len(set(seen))


def test_results_are_ordered_by_score(roster):
    scores = [m.score for m in search(roster, Query("classroom teacher hindi", limit=50))]
    assert scores == sorted(scores, reverse=True)


def test_ordering_is_stable_across_runs(roster):
    query = Query("classroom teacher hindi", limit=20)
    assert [m.look.id for m in search(roster, query)] == [m.look.id for m in search(roster, query)]


def test_ordering_does_not_depend_on_roster_order(roster):
    query = Query("classroom teacher hindi", limit=20)
    forward = [m.look.id for m in search(roster, query)]
    backward = [m.look.id for m in search(list(reversed(roster)), query)]
    assert forward == backward


def test_the_limit_is_honoured(roster):
    assert len(search(roster, Query("hindi", limit=5))) == 5


def test_an_empty_query_returns_nothing_rather_than_everything(roster):
    """A blank box is not a request for the whole roster in arbitrary order."""
    assert search(roster, Query("   ")) == []


def test_zero_scoring_candidates_are_not_returned(roster):
    """Padding a short result list with irrelevant people is worse than a short
    result list."""
    assert all(m.score > 0 for m in search(roster, Query("classroom", limit=200)))


def test_search_never_selects(roster):
    """It ranks and explains. There is no chosen flag to render as a default."""
    assert set(Match.__slots__).isdisjoint({"selected", "chosen", "recommended"})


# ------------------------------------------------------------ the type tabs

def test_the_kind_filter_is_the_only_thing_that_removes_a_candidate(roster):
    human = search(roster, Query("hindi", kind=Kind.HUMAN, limit=200))
    ai = search(roster, Query("hindi", kind=Kind.AI, limit=200))
    both = search(roster, Query("hindi", limit=200))
    assert {m.actor.kind for m in human} == {Kind.HUMAN}
    assert {m.actor.kind for m in ai} == {Kind.AI}
    assert len(both) == len(human) + len(ai)


# --------------------------------------------------------------- candidates

def test_the_scorer_sees_the_person_and_the_look_together(roster):
    """A right read in the wrong room is a partial match, which is only
    expressible if both are in the text being scored."""
    actor = roster[0]
    text = candidate_text(actor, actor.looks[0])
    assert actor.delivery in text
    assert actor.looks[0].scene in text


def test_candidate_text_is_the_only_matchable_surface(roster):
    actor = next(a for a in roster if a.id == "P001")
    text = candidate_text(actor, actor.looks[0])
    assert actor.appearance in text and "Hindi" in text


# ------------------------------------------------------------------- model

def test_a_model_score_replaces_the_lexical_one(roster):
    target = roster[0].looks[0]
    client = StubClient(overrides=[{"id": target.id, "fit": 0.9,
                                    "evidence": [roster[0].delivery]}])
    match = next(m for m in search(roster, Query("anything", limit=200), client)
                 if m.look.id == target.id)
    assert match.source == "model" and match.score == 0.9


def test_a_partial_model_response_falls_back_entirely(roster):
    """Mixing scorers within one list ranks two incompatible numbers against
    each other: a 0.95 judgement beside a 0.20 word count. Observed live — the
    model answered only the candidates it liked and left the rest to word
    overlap, which then out-ranked genuine matches further down."""
    everything = [look.id for actor in roster for look in actor.looks]
    client = StubClient(drop=everything[5:])
    matches = search(roster, Query("classroom", limit=200), client)
    assert matches and all(m.source == "lexical" for m in matches)


def test_a_complete_response_is_used_whole(roster):
    matches = search(roster, Query("classroom", limit=200), StubClient())
    assert matches and all(m.source == "model" for m in matches)


def test_candidates_the_model_did_not_score_fall_back_rather_than_vanish(roster):
    client = StubClient(payload={"results": []})
    matches = search(roster, Query("classroom", limit=200), client)
    assert matches and all(m.source == "lexical" for m in matches)


def test_evidence_not_quoted_from_the_profile_is_discarded(roster):
    """The point of evidence is that it is a citation. A phrase the model wrote
    itself is a claim about the record, and those are the ones that turn out to
    be flattering and false."""
    target = roster[0].looks[0]
    client = StubClient(overrides=[{
        "id": target.id, "fit": 0.8,
        "evidence": ["radiates natural warmth", roster[0].delivery],
    }])
    match = next(m for m in search(roster, Query("warm", limit=200), client)
                 if m.look.id == target.id)
    assert match.evidence == (roster[0].delivery,)


def test_evidence_is_capped_at_three_phrases(roster):
    actor = roster[0]
    client = StubClient(overrides=[{
        "id": actor.looks[0].id, "fit": 0.8,
        "evidence": [actor.delivery, actor.appearance, actor.looks[0].scene,
                     actor.looks[0].wardrobe],
    }])
    match = next(m for m in search(roster, Query("x", limit=200), client)
                 if m.look.id == actor.looks[0].id)
    assert len(match.evidence) == 3


def test_scores_are_clamped(roster):
    client = StubClient(overrides=[{"id": roster[0].looks[0].id, "fit": 7.0}])
    assert max(m.score for m in search(roster, Query("x", limit=200), client)) <= 1.0


def test_a_malformed_score_is_discarded_not_coerced(roster):
    client = StubClient(overrides=[{"id": roster[0].looks[0].id, "fit": "great"}])
    matches = search(roster, Query("classroom", limit=200), client)
    assert all(m.source == "lexical" for m in matches)


def test_an_unknown_id_from_the_model_is_ignored(roster):
    client = StubClient(payload={"results": [{"id": "not-a-look", "fit": 1.0}]})
    matches = search(roster, Query("classroom", limit=200), client)
    assert all(m.look.id != "not-a-look" for m in matches)


def test_a_failed_model_call_degrades_rather_than_erroring(roster):
    class Failing:
        available = True
        def json(self, prompt, schema):
            return None

    matches = search(roster, Query("classroom", limit=10), Failing())
    assert matches and all(m.source == "lexical" for m in matches)


def test_candidates_are_batched_not_sent_one_per_call(roster):
    client = StubClient()
    total = sum(len(a.looks) for a in roster)
    search(roster, Query("x", limit=200), client)
    assert client.calls == -(-total // BATCH)      # ceiling division
    assert client.calls < total


def test_the_prompt_tells_the_model_the_vocabularies_differ(roster):
    """Without that instruction the model quietly rewards shared wording, which
    is the failure the disjoint banks exist to expose."""
    client = StubClient()
    search(roster, Query("someone warm", limit=10), client)
    assert "does not reuse the words" in client.prompts[0]


# ----------------------------------------------------------------- lexical

def test_the_lexical_fallback_finds_literal_words():
    score, hits = lexical_score("classroom teacher", "classroom. whiteboard half-wiped.")
    assert score == 0.5 and hits == ("classroom",)


def test_the_lexical_fallback_cannot_bridge_the_vocabulary_gap(roster):
    """This is a demonstration, not a defect.

    P001 is written to answer "someone warm" without containing a single word
    anyone would type for it. Word overlap scores her at zero, which is the
    honest measure of what the fallback is worth and why the key matters.
    """
    priya = next(a for a in roster if a.id == "P001")
    score, _ = lexical_score("someone warm and approachable", candidate_text(priya, priya.looks[0]))
    assert score == 0.0


def test_stopwords_do_not_manufacture_a_score(roster):
    score, _ = lexical_score("I am looking for someone who would be a person",
                             candidate_text(roster[0], roster[0].looks[0]))
    assert score == 0.0
