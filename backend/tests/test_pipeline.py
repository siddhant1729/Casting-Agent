"""Orchestration and the seeded examples."""

from __future__ import annotations

import pytest

from casting.domain.models import Kind, Query
from casting.pipeline import EXAMPLE_QUERIES, from_text, run
from casting.reasoning.explain import resolve_citation


def test_three_seeded_examples_exist():
    """The first screen is never empty."""
    assert len(EXAMPLE_QUERIES) == 3
    assert all(e["label"] and e["text"] for e in EXAMPLE_QUERIES)


def test_every_seeded_example_returns_something():
    for example in EXAMPLE_QUERIES:
        assert from_text(example["text"]).items


def test_ranks_are_dense_and_ordered():
    results = from_text(EXAMPLE_QUERIES[0]["text"])
    assert [i.rank for i in results.items] == list(range(1, len(results.items) + 1))


def test_scores_descend():
    scores = [i.match.score for i in from_text(EXAMPLE_QUERIES[1]["text"]).items]
    assert scores == sorted(scores, reverse=True)


def test_results_without_a_model_say_which_scorer_ran():
    """A ranking produced by word overlap is a different artefact from one a
    model produced, and the UI reads this to say which it is showing."""
    results = from_text(EXAMPLE_QUERIES[0]["text"])
    assert results.scorer == "lexical"
    assert results.model_used is False


def test_the_kind_filter_narrows_the_result():
    everyone = from_text(EXAMPLE_QUERIES[0]["text"], limit=100)
    humans = from_text(EXAMPLE_QUERIES[0]["text"], kind=Kind.HUMAN, limit=100)
    assert len(humans.items) < len(everyone.items)
    assert all(i.match.actor.kind is Kind.HUMAN for i in humans.items)


def test_an_empty_query_returns_no_items_and_does_not_error():
    results = from_text("   ")
    assert results.items == ()
    assert results.roster_size > 0


def test_the_seed_changes_the_roster():
    a = from_text(EXAMPLE_QUERIES[0]["text"], seed=7)
    b = from_text(EXAMPLE_QUERIES[0]["text"], seed=23)
    assert [i.match.actor.name for i in a.items] != [i.match.actor.name for i in b.items]


def test_results_report_the_roster_they_searched():
    results = from_text(EXAMPLE_QUERIES[0]["text"])
    assert results.roster_size == 45
    assert results.look_count > results.roster_size


@pytest.mark.parametrize("seed", [1, 2, 3, 11, 23])
def test_results_hold_across_independently_seeded_rosters(seed):
    """The robustness bar in its testable form: no seeded query returns an
    empty screen, and no rationale cites a field its record lacks."""
    for example in EXAMPLE_QUERIES:
        results = from_text(example["text"], seed=seed)
        assert results.items
        for item in results.items:
            for path in item.rationale.cites + item.reservation.cites:
                resolve_citation(path, item.match.actor, item.match.look, results.query)


def test_every_item_carries_a_rationale_and_exactly_one_reservation():
    for item in from_text(EXAMPLE_QUERIES[2]["text"]).items:
        assert item.rationale.text and item.reservation.text
