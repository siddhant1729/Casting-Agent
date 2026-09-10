"""Why this person, and what you are trading off.

Both are derived, not written.

The rationale is assembled around phrases quoted verbatim from the candidate's
own profile, and every sentence carries the record fields it was built from.
`resolve_citation` walks those paths back to a live value, so "no unsupported
claims" is a property the tests check rather than a promise the README makes.

The reservation is *selected* from a closed set of structural facts, with the
model's own caveat allowed in as one member. Requiring a written reservation on
every candidate would force an invention whenever a match is genuinely clean —
so "no material reservation" is a member of the set too.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..domain.models import LANGUAGE_NAMES, Actor, Fluency, Look, Query, Setting
from .search import Match

LOW_CONFIDENCE = 0.5


# ------------------------------------------------------------- provenance

def resolve_citation(path: str, actor: Actor, look: Look, query: Query):
    """Walk a citation path back to the value it claims. Raises if it cannot.

    A sentence citing `actor.temperament` fails here rather than shipping as a
    confident claim about a field that does not exist.
    """
    root, _, attribute = path.partition(".")
    source = {"actor": actor, "look": look, "query": query}.get(root)
    if source is None or not attribute or not hasattr(source, attribute):
        raise KeyError(f"unresolvable citation: {path}")
    return getattr(source, attribute)


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    cites: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Rationale:
    sentences: tuple[Sentence, ...]

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.sentences)

    @property
    def cites(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(c for s in self.sentences for c in s.cites))


def _listed(items) -> str:
    items = [i for i in items if i]
    if len(items) < 2:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


# -------------------------------------------------------------- rationale

def _match_sentence(match: Match) -> Sentence:
    if match.evidence:
        quoted = _listed([f'"{phrase}"' for phrase in match.evidence])
        return Sentence(
            f"Matched on {quoted}.",
            ("actor.delivery", "actor.appearance", "look.scene"),
        )
    return Sentence(
        f"Delivery reads \"{match.actor.delivery}\".",
        ("actor.delivery",),
    )


def _look_sentence(match: Match) -> Sentence:
    look = match.look
    return Sentence(
        f"The {look.setting.value} look is {look.scene}, in {look.wardrobe}.",
        ("look.setting", "look.scene", "look.wardrobe"),
    )


def _who_sentence(match: Match) -> Sentence:
    actor = match.actor
    count = len(actor.looks)
    return Sentence(
        f"{actor.presents_as.capitalize()}, {actor.age_band}, speaking "
        f"{actor.language_text}; {count} look{'' if count == 1 else 's'} on file.",
        ("actor.presents_as", "actor.age_band", "actor.languages", "actor.looks"),
    )


def rationale(match: Match) -> Rationale:
    """Three sentences, every claim traceable to a field."""
    return Rationale((_match_sentence(match), _look_sentence(match), _who_sentence(match)))


# ------------------------------------------------------------ reservation

class ReservationKind(StrEnum):
    MODEL_CAVEAT = "model_caveat"
    LANGUAGE_MISSING = "language_missing"
    LANGUAGE_THIN = "language_thin"
    SETTING_ABSENT = "setting_absent"
    LOW_CONFIDENCE = "low_confidence"
    FEW_LOOKS = "few_looks"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Reservation:
    kind: ReservationKind
    text: str
    cites: tuple[str, ...]


def mentioned_languages(text: str) -> tuple[str, ...]:
    """Language names are a closed vocabulary, so this is a lookup, not parsing."""
    lowered = text.lower()
    return tuple(code for code, name in LANGUAGE_NAMES.items() if name.lower() in lowered)


def mentioned_settings(text: str) -> tuple[Setting, ...]:
    lowered = text.lower()
    return tuple(s for s in Setting if s.value in lowered)


def _language_gap(match: Match, query: Query):
    for code in mentioned_languages(query.text):
        level = match.actor.languages.get(code)
        name = LANGUAGE_NAMES[code]
        if level is None:
            return Reservation(
                ReservationKind.LANGUAGE_MISSING,
                f"No {name} on file, and you asked for it.",
                ("actor.languages", "query.text"),
            )
        if level is Fluency.CONVERSATIONAL:
            return Reservation(
                ReservationKind.LANGUAGE_THIN,
                f"{name} is conversational, not native — worth a read test before "
                f"committing a whole shoot to it.",
                ("actor.languages", "query.text"),
            )
    return None


def _setting_gap(match: Match, query: Query):
    wanted = mentioned_settings(query.text)
    if not wanted:
        return None
    available = {look.setting for look in match.actor.looks}
    if match.look.setting in wanted:
        return None
    if not (available & set(wanted)):
        asked = _listed([s.value for s in wanted])
        return Reservation(
            ReservationKind.SETTING_ABSENT,
            f"No {asked} look on file — this is a {match.look.setting.value} look, "
            f"ranking on the person rather than the room.",
            ("look.setting", "actor.looks", "query.text"),
        )
    return None


def _model_caveat(match: Match, query: Query):
    if match.caveat:
        return Reservation(ReservationKind.MODEL_CAVEAT, match.caveat, ("actor.profile_text",))
    return None


def _low_confidence(match: Match, query: Query):
    if match.score < LOW_CONFIDENCE:
        return Reservation(
            ReservationKind.LOW_CONFIDENCE,
            f"A partial match at {match.score:.0%} — they answer some of what you "
            f"described, not all of it.",
            ("actor.profile_text",),
        )
    return None


def _few_looks(match: Match, query: Query):
    if len(match.actor.looks) < 2:
        return Reservation(
            ReservationKind.FEW_LOOKS,
            "One look on file, so there is no second setting to cut to.",
            ("actor.looks",),
        )
    return None


#: Ordered by how much each should worry the user. Exactly one is returned.
RESERVATION_CHECKS = (
    _language_gap,
    _setting_gap,
    _model_caveat,
    _low_confidence,
    _few_looks,
)

NO_RESERVATION = Reservation(
    ReservationKind.NONE,
    "Nothing on the record argues against them, which is not the same as saying "
    "they are right for it.",
    (),
)


def reservation(match: Match, query: Query) -> Reservation:
    """Exactly one, selected from the closed set above."""
    for check in RESERVATION_CHECKS:
        found = check(match, query)
        if found is not None:
            return found
    return NO_RESERVATION
