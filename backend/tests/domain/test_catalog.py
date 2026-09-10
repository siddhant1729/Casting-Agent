"""Catalog integrity."""

from __future__ import annotations

import re

import pytest

from casting.domain import vocab
from casting.domain.catalog import build_roster, roster_looks
from casting.domain.models import Kind, Setting


def _catalog_words(actor) -> set[str]:
    text = " ".join(
        [actor.appearance, actor.delivery, " ".join(actor.voice)]
        + [f"{l.scene} {l.wardrobe} {' '.join(l.framing)}" for l in actor.looks]
    ).lower()
    return set(re.findall(r"[a-z-]+", text))


def test_vocabulary_banks_are_disjoint():
    """The load-bearing test of the whole product.

    If the catalog described people using the words a request is written in,
    ranking would be a string match dressed up as understanding.
    """
    catalog_text = " ".join(
        vocab.APPEARANCE_HAIR + vocab.APPEARANCE_FACE + vocab.APPEARANCE_BUILD
        + vocab.DELIVERY_PACE + vocab.DELIVERY_TEXTURE + vocab.DELIVERY_STANCE
        + vocab.VOICE_TAGS + vocab.FRAMING
        + tuple(w for group in vocab.WARDROBE.values() for w in group)
        + tuple(s for group in vocab.SCENE.values() for s in group)
    ).lower()
    assert set(re.findall(r"[a-z-]+", catalog_text)).isdisjoint(vocab.QUERY_TERMS)


@pytest.mark.parametrize("seed", [1, 7, 23])
def test_generated_profiles_never_use_query_vocabulary(seed):
    """Enforced on output, not only on the banks."""
    for actor in build_roster(seed):
        assert _catalog_words(actor).isdisjoint(vocab.QUERY_TERMS), actor.id


def test_roster_is_deterministic_for_a_seed():
    a, b = build_roster(42), build_roster(42)
    assert [x.id for x in a] == [x.id for x in b]
    assert [x.appearance for x in a] == [x.appearance for x in b]
    assert [x.delivery for x in a] == [x.delivery for x in b]


def test_different_seeds_give_different_rosters():
    generated = lambda roster: [a.name + a.delivery for a in roster if not a.planted]
    assert generated(build_roster(1)) != generated(build_roster(2))


def test_planted_actors_survive_every_seed():
    expected = {
        "warm_without_the_word_warm",
        "urgent_not_warm",
        "teacher_delivery_no_classroom",
        "classroom_look_wrong_read",
        "single_look_ai_actor",
    }
    for seed in (1, 2, 3, 99):
        assert {a.planted for a in build_roster(seed) if a.planted} == expected


def test_the_warm_planted_actor_never_says_warm():
    """P001 exists to be found by a query for someone warm, using a profile in
    which no synonym of the word appears. If this ever fails, the case stops
    testing anything."""
    priya = next(a for a in build_roster(7) if a.id == "P001")
    assert _catalog_words(priya).isdisjoint({"warm", "friendly", "approachable", "kind"})


def test_looks_are_the_ranking_unit_and_outnumber_actors():
    roster = build_roster(5)
    assert len(roster_looks(roster)) > len(roster)
    assert all(2 <= len(a.looks) <= 5 for a in roster if not a.planted)


def test_look_ids_are_unique_and_settings_do_not_repeat_within_an_actor():
    roster = build_roster(5)
    ids = [look.id for _, look in roster_looks(roster)]
    assert len(ids) == len(set(ids))
    for actor in roster:
        settings = [look.setting for look in actor.looks]
        assert len(settings) == len(set(settings)), actor.id


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_setting_is_represented(seed):
    assert {look.setting for _, look in roster_looks(build_roster(seed))} == set(Setting)


def test_both_actor_kinds_are_present():
    """The product already has an AI / Human tab; the roster has to feed it."""
    kinds = {a.kind for a in build_roster(5)}
    assert kinds == {Kind.HUMAN, Kind.AI}


def test_profile_text_carries_everything_a_scorer_needs():
    """The scorer sees only this string. Anything missing from it is invisible
    to ranking, however carefully it was modelled."""
    actor = next(a for a in build_roster(7) if a.id == "P003")
    text = actor.profile_text
    assert actor.appearance in text
    assert actor.delivery in text
    assert "Tamil" in text and "English" in text
    assert actor.age_band in text and actor.presents_as in text


def test_look_profile_text_describes_the_room():
    look = next(a for a in build_roster(7) if a.id == "P001").looks[0]
    assert look.scene in look.profile_text
    assert look.wardrobe in look.profile_text
    assert look.setting.value in look.profile_text


def test_no_pricing_or_usage_fields_survive_on_the_records():
    """Usage is covered by membership. A stray rate field would put a number
    back on a card that the product has no business showing."""
    actor = build_roster(7)[0]
    for gone in ("base_rate", "territory_rates", "exclusivity_premium",
                 "holds", "category_blocks"):
        assert not hasattr(actor, gone), gone
