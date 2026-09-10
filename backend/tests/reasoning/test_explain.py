"""Rationale provenance and selected reservations."""

from __future__ import annotations

import pytest

from casting.domain.catalog import build_roster
from casting.domain.models import Fluency, Query, Setting
from casting.reasoning.explain import (
    RESERVATION_CHECKS,
    ReservationKind,
    mentioned_languages,
    mentioned_settings,
    rationale,
    reservation,
    resolve_citation,
)
from casting.reasoning.search import Match, search


@pytest.fixture
def roster():
    return build_roster(7)


@pytest.fixture
def query():
    return Query("someone patient at a whiteboard, Hindi and Tamil", limit=20)


@pytest.fixture
def matches(roster, query):
    return search(roster, query)


def make_match(actor, look, score=0.8, evidence=(), caveat=None, source="model"):
    return Match(actor=actor, look=look, score=score, evidence=evidence,
                 caveat=caveat, source=source)


# -------------------------------------------------------------- provenance

def test_every_cited_field_resolves_on_the_record(matches, query):
    """Enforced rather than reviewed. A sentence citing `actor.temperament`
    fails here instead of shipping as a confident claim about a field that does
    not exist."""
    for match in matches:
        for sentence in rationale(match).sentences:
            for path in sentence.cites:
                resolve_citation(path, match.actor, match.look, query)


def test_an_unresolvable_citation_raises(matches, query):
    match = matches[0]
    with pytest.raises(KeyError):
        resolve_citation("actor.temperament", match.actor, match.look, query)
    with pytest.raises(KeyError):
        resolve_citation("vibes", match.actor, match.look, query)


def test_every_sentence_carries_at_least_one_citation(matches):
    for match in matches:
        for sentence in rationale(match).sentences:
            assert sentence.cites, sentence.text


def test_rationale_is_two_to_three_sentences(matches):
    for match in matches:
        assert 2 <= len(rationale(match).sentences) <= 3


def test_evidence_is_quoted_verbatim_into_the_rationale(roster):
    actor = roster[0]
    match = make_match(actor, actor.looks[0], evidence=(actor.delivery,))
    assert f'"{actor.delivery}"' in rationale(match).text


def test_a_match_without_evidence_still_says_something_grounded(roster):
    actor = roster[0]
    text = rationale(make_match(actor, actor.looks[0], evidence=())).text
    assert actor.delivery in text


def test_the_look_sentence_describes_the_actual_look(matches):
    for match in matches:
        text = rationale(match).text
        assert match.look.scene in text and match.look.wardrobe in text


def test_the_rationale_never_states_a_price(matches):
    """Usage is covered by membership. A number here would be inventing a
    concern the product does not have."""
    for match in matches:
        assert "₹" not in rationale(match).text


# ------------------------------------------------------------- reservation

def test_exactly_one_reservation_per_match(matches, query):
    for match in matches:
        found = reservation(match, query)
        assert isinstance(found.kind, ReservationKind) and found.text


def test_every_reservation_comes_from_the_closed_set(matches, query):
    allowed = set(ReservationKind)
    for match in matches:
        assert reservation(match, query).kind in allowed


def test_reservation_citations_resolve(matches, query):
    for match in matches:
        found = reservation(match, query)
        for path in found.cites:
            resolve_citation(path, match.actor, match.look, query)


def test_a_clean_match_says_so_rather_than_inventing_a_doubt(roster):
    """Forcing a written reservation onto a clean match forces an invention.
    NONE is a member of the closed set for that reason."""
    devika = next(a for a in roster if a.id == "P003")
    match = make_match(devika, devika.looks[0], score=0.95)
    assert reservation(match, Query("someone measured")).kind is ReservationKind.NONE


def test_a_missing_language_is_reported_when_it_was_asked_for(roster):
    rohan = next(a for a in roster if a.id == "P004")
    assert "ta" not in rohan.languages
    found = reservation(make_match(rohan, rohan.looks[0]), Query("teacher, Tamil please"))
    assert found.kind is ReservationKind.LANGUAGE_MISSING
    assert "Tamil" in found.text


def test_a_conversational_language_is_flagged_as_thin(roster):
    rohan = next(a for a in roster if a.id == "P004")
    assert rohan.languages["en"] is Fluency.CONVERSATIONAL
    found = reservation(make_match(rohan, rohan.looks[0]), Query("someone for English VO"))
    assert found.kind is ReservationKind.LANGUAGE_THIN


def test_a_language_not_asked_for_is_not_a_reservation(roster):
    rohan = next(a for a in roster if a.id == "P004")
    assert reservation(make_match(rohan, rohan.looks[0]),
                       Query("someone quick")).kind is not ReservationKind.LANGUAGE_MISSING


def test_the_right_person_in_the_wrong_room_is_disclosed(roster):
    """P003's read answers a teaching query exactly and she has no classroom
    look. Ranking her without saying so is the failure this catches."""
    devika = next(a for a in roster if a.id == "P003")
    assert Setting.CLASSROOM not in {l.setting for l in devika.looks}
    found = reservation(make_match(devika, devika.looks[0]),
                        Query("a teacher in a classroom"))
    assert found.kind is ReservationKind.SETTING_ABSENT
    assert "classroom" in found.text


def test_an_actor_who_has_the_asked_for_setting_elsewhere_is_not_flagged(roster):
    """They do have that look; you are just reading a different card of theirs."""
    rohan = next(a for a in roster if a.id == "P004")
    other = next(l for l in rohan.looks if l.setting is not Setting.CLASSROOM)
    found = reservation(make_match(rohan, other), Query("classroom explainer"))
    assert found.kind is not ReservationKind.SETTING_ABSENT


def test_the_models_own_caveat_is_used_when_it_offers_one(roster):
    actor = roster[0]
    match = make_match(actor, actor.looks[0], caveat="reads younger than the brief suggests")
    found = reservation(match, Query("someone senior"))
    assert found.kind is ReservationKind.MODEL_CAVEAT
    assert found.text == "reads younger than the brief suggests"


def test_a_weak_match_is_labelled_as_partial(roster):
    actor = roster[0]
    found = reservation(make_match(actor, actor.looks[0], score=0.2), Query("anything"))
    assert found.kind is ReservationKind.LOW_CONFIDENCE
    assert "20%" in found.text


def test_a_single_look_actor_is_flagged(roster):
    zoya = next(a for a in roster if a.id == "P005")
    found = reservation(make_match(zoya, zoya.looks[0], score=0.9), Query("beach"))
    assert found.kind is ReservationKind.FEW_LOOKS


def test_reservation_precedence_is_stable_and_total(roster):
    """Reordering these silently changes every card in the product."""
    assert [c.__name__ for c in RESERVATION_CHECKS] == [
        "_language_gap", "_setting_gap", "_model_caveat",
        "_low_confidence", "_few_looks",
    ]


def test_no_check_raises_on_a_bare_query(matches):
    for match in matches:
        reservation(match, Query("x"))


# ------------------------------------------------------- closed vocabularies

def test_language_mentions_are_a_lookup_not_a_parse():
    assert mentioned_languages("Hindi and Tamil please") == ("hi", "ta")
    assert mentioned_languages("nothing about language here") == ()


def test_setting_mentions_are_a_lookup_not_a_parse():
    assert mentioned_settings("a classroom or an office") == (Setting.OFFICE, Setting.CLASSROOM)
    assert mentioned_settings("somebody friendly") == ()
