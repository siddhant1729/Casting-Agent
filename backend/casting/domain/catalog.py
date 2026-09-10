"""Synthetic roster generation.

The catalog is synthetic, labelled as such in-product, and regenerable from a
visible seed. Bios and look descriptions are assembled only from the catalog
side of `vocab`, which shares no term with the language a query is written in.

Reseeding does not, on its own, defeat the circularity objection — it resamples
a distribution the author designed. What defeats it is the vocabulary split,
plus the planted cases below, which exist to be searched for and missed.

Portraits are abstract geometry drawn from a deterministic seed, never a
generated photoreal face: generated faces can resemble real people, which is
the thing that rule exists to prevent.
"""

from __future__ import annotations

import random

from . import vocab
from .models import LANGUAGES, Actor, Fluency, Kind, Look, Setting


def _appearance(rng: random.Random) -> str:
    return "{}, {}, {}.".format(
        rng.choice(vocab.APPEARANCE_BUILD).capitalize(),
        rng.choice(vocab.APPEARANCE_HAIR),
        rng.choice(vocab.APPEARANCE_FACE),
    )


def _delivery(rng: random.Random) -> str:
    return "{}, {}, {}".format(
        rng.choice(vocab.DELIVERY_PACE),
        rng.choice(vocab.DELIVERY_TEXTURE),
        rng.choice(vocab.DELIVERY_STANCE),
    )


def _look(rng: random.Random, actor_id: str, index: int, setting: Setting) -> Look:
    return Look(
        id=f"{actor_id}-L{index}",
        actor_id=actor_id,
        setting=setting,
        scene=rng.choice(vocab.SCENE[setting.value]),
        wardrobe=rng.choice(vocab.WARDROBE[setting.value]),
        framing=tuple(rng.sample(vocab.FRAMING, k=rng.randint(2, 3))),
    )


def _languages(rng: random.Random) -> dict[str, Fluency]:
    langs: dict[str, Fluency] = {"hi": Fluency.NATIVE}
    langs["en"] = rng.choice(
        [Fluency.NATIVE, Fluency.FLUENT, Fluency.FLUENT, Fluency.CONVERSATIONAL]
    )
    for extra in rng.sample([l for l in LANGUAGES if l not in langs], k=rng.randint(0, 2)):
        langs[extra] = rng.choice([Fluency.NATIVE, Fluency.FLUENT, Fluency.CONVERSATIONAL])
    return langs


def _actor(rng: random.Random, index: int) -> Actor:
    actor_id = f"A{index:03d}"
    settings = rng.sample(list(Setting), k=rng.randint(2, 5))
    return Actor(
        id=actor_id,
        name=f"{rng.choice(vocab.FIRST_NAMES)} {rng.choice(vocab.LAST_INITIALS)}.",
        kind=Kind.AI if rng.random() < 0.3 else Kind.HUMAN,
        age_band=rng.choice(vocab.AGE_BANDS),
        presents_as=rng.choice(vocab.PRESENTS_AS),
        languages=_languages(rng),
        appearance=_appearance(rng),
        delivery=_delivery(rng),
        voice=tuple(rng.sample(vocab.VOICE_TAGS, k=2)),
        looks=tuple(_look(rng, actor_id, i, s) for i, s in enumerate(settings, start=1)),
    )


# --------------------------------------------------------------- edge cases

def _planted() -> list[Actor]:
    """Fixed actors that exist to be searched for.

    Identical under every seed, so the tests that check whether search actually
    understands a description do not depend on the RNG obliging.
    """
    def look(actor_id, i, setting, scene, wardrobe, framing):
        return Look(f"{actor_id}-L{i}", actor_id, setting, scene, wardrobe, framing)

    return [
        # 1. The vocabulary gap in one record. Every word a user would type for
        #    this person — warm, approachable, reassuring — is absent from the
        #    text. A lexical scorer cannot reach her; a semantic one should.
        Actor(
            id="P001",
            name="Priya M.",
            kind=Kind.HUMAN,
            age_band="35-44",
            presents_as="woman",
            languages={"hi": Fluency.NATIVE, "en": Fluency.FLUENT, "mr": Fluency.NATIVE},
            appearance="Settles into a chair the moment she can, a plait over one shoulder, laugh lines that arrive before the laugh.",
            delivery="unhurried, with the vowels of somebody's older cousin, explains without condescending",
            voice=("mid-register", "even-toned"),
            looks=(
                look("P001", 1, Setting.HOME, "kitchen counter, afternoon light through a grille window", "worn cotton tee", ("handheld", "natural-light")),
                look("P001", 2, Setting.STUDIO, "seamless grey, one hard key and a bounce", "plain crew neck", ("tripod-locked", "waist-up")),
            ),
            planted="warm_without_the_word_warm",
        ),
        # 2. The opposite read, so a query for one must not return the other.
        Actor(
            id="P002",
            name="Arjun T.",
            kind=Kind.HUMAN,
            age_band="25-34",
            presents_as="man",
            languages={"hi": Fluency.NATIVE, "en": Fluency.NATIVE},
            appearance="Compact and square-shouldered, shaved at the sides, longer on top, a jaw you notice in profile.",
            delivery="clipped, almost impatient, declarative, sells nothing, states things",
            voice=("bright", "clipped"),
            looks=(
                look("P002", 1, Setting.OFFICE, "glass meeting room, blinds half-drawn", "blazer over tee", ("tripod-locked", "direct-address")),
                look("P002", 2, Setting.STREET, "market lane, foot traffic behind", "bomber jacket", ("handheld", "walking")),
                look("P002", 3, Setting.GYM, "mirrored wall, chalk on the hands", "training vest", ("handheld", "wide-frame")),
            ),
            planted="urgent_not_warm",
        ),
        # 3. Right person, wrong room. Her delivery answers a teaching query
        #    exactly; none of her looks is a classroom. The card has to say so
        #    rather than quietly ranking her first.
        Actor(
            id="P003",
            name="Devika R.",
            kind=Kind.HUMAN,
            age_band="45-54",
            presents_as="woman",
            languages={"hi": Fluency.FLUENT, "en": Fluency.NATIVE, "ta": Fluency.NATIVE},
            appearance="Stands very straight, always, greying at the temples, wire-frame glasses pushed up constantly.",
            delivery="measured, clean and unadorned, talks you through it the way a colleague would",
            voice=("low-register", "resonant"),
            looks=(
                look("P003", 1, Setting.HOME, "balcony doorway with plants crowding the frame", "house kurta", ("natural-light", "waist-up")),
                look("P003", 2, Setting.STUDIO, "white infinity, flat and even", "light blazer", ("tripod-locked", "direct-address")),
            ),
            planted="teacher_delivery_no_classroom",
        ),
        # 4. The classroom look, on someone whose read is nothing like teaching.
        #    Setting and person pull in opposite directions on the same query.
        Actor(
            id="P004",
            name="Rohan K.",
            kind=Kind.HUMAN,
            age_band="25-34",
            presents_as="man",
            languages={"hi": Fluency.NATIVE, "en": Fluency.CONVERSATIONAL},
            appearance="Long-limbed, all elbows on camera, curls cut short, a scar through one eyebrow.",
            delivery="quick-footed, conversational to the point of rambling, leans into the camera",
            voice=("airy", "nasal-forward"),
            looks=(
                look("P004", 1, Setting.CLASSROOM, "whiteboard half-wiped, marker still in hand", "collared shirt with pens", ("tripod-locked", "direct-address")),
                look("P004", 2, Setting.CAFE, "corner table, cup between both hands", "denim shirt", ("shallow-depth", "seated")),
            ),
            planted="classroom_look_wrong_read",
        ),
        # 5. One look, and an AI actor — the type filter has something to bite on.
        Actor(
            id="P005",
            name="Zoya A.",
            kind=Kind.AI,
            age_band="18-24",
            presents_as="woman",
            languages={"hi": Fluency.NATIVE, "en": Fluency.FLUENT},
            appearance="Slight, and uses the whole frame anyway, a centre parting that never quite holds, freckles across the bridge of the nose.",
            delivery="brisk, with a smile audible under it, treats the viewer as a peer",
            voice=("bright", "breathy"),
            looks=(
                look("P005", 1, Setting.BEACH, "shoreline at golden hour, squinting slightly", "sun-faded tee", ("handheld", "walking")),
            ),
            planted="single_look_ai_actor",
        ),
    ]


def build_roster(seed: int, size: int = 40) -> list[Actor]:
    """Deterministic roster for a visible seed."""
    rng = random.Random(seed)
    return _planted() + [_actor(rng, i) for i in range(1, size + 1)]


def roster_looks(roster: list[Actor]) -> list[tuple[Actor, Look]]:
    """Flatten to the ranking unit."""
    return [(actor, look) for actor in roster for look in actor.looks]


def search_by_name(roster: list[Actor], term: str) -> list[Actor]:
    """Substring match on the actor's name. Nothing else.

    This is the roster's existing search, reproduced honestly. It is
    deliberately not improved: matching on the profile text as well would make
    it a weak second ranker sitting behind the real one, and a name lookup that
    quietly starts answering descriptions is the harder thing to reason about.

    A blank term returns the whole roster, which is what a grid with an empty
    search box shows.
    """
    needle = term.strip().lower()
    if not needle:
        return list(roster)
    return [actor for actor in roster if needle in actor.name.lower()]
