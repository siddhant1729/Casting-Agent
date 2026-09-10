"""Core records.

The product is a search over people, so the schema carries only what describes
a person and what you would see on screen. There are no rates, no territories,
no exclusivity holds and no budget: usage is covered by membership, and pricing
a decision that has already been paid for would be noise on the card.

`Actor.profile_text` and `Look.profile_text` are the searchable surfaces. They
are the only things the ranker ever sees, which keeps "what was matched" a
question with a literal answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Kind(StrEnum):
    """Mirrors the type filter the product already has."""
    HUMAN = "human"
    AI = "ai"


class Setting(StrEnum):
    STUDIO = "studio"
    HOME = "home"
    OFFICE = "office"
    OUTDOOR = "outdoor"
    CLASSROOM = "classroom"
    BEACH = "beach"
    STREET = "street"
    CAFE = "cafe"
    GYM = "gym"


class Fluency(StrEnum):
    NATIVE = "native"
    FLUENT = "fluent"
    CONVERSATIONAL = "conversational"


LANGUAGES = ("hi", "en", "ta", "te", "bn", "mr", "kn", "gu")

LANGUAGE_NAMES = {
    "hi": "Hindi", "en": "English", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "mr": "Marathi", "kn": "Kannada", "gu": "Gujarati",
}


@dataclass(frozen=True, slots=True)
class Look:
    """One shootable presentation of an actor. The ranking unit.

    A classroom look and a beach look are different casting decisions with the
    same face, which is why the roster is searched at this granularity rather
    than at actor granularity.
    """
    id: str
    actor_id: str
    setting: Setting
    scene: str          # what you see: the environment, the light, the framing
    wardrobe: str
    framing: tuple[str, ...]

    @property
    def profile_text(self) -> str:
        return f"{self.setting.value}. {self.scene}. Wearing {self.wardrobe}. {', '.join(self.framing)}."


@dataclass(frozen=True, slots=True)
class Actor:
    id: str
    name: str
    kind: Kind
    age_band: str
    presents_as: str
    languages: dict[str, Fluency]

    appearance: str          # what they look like, in a caster's words
    delivery: str            # how they read a line
    voice: tuple[str, ...]

    looks: tuple[Look, ...]
    planted: str | None = None

    @property
    def language_text(self) -> str:
        return ", ".join(
            f"{LANGUAGE_NAMES.get(code, code)} ({level.value})"
            for code, level in self.languages.items()
        )

    @property
    def profile_text(self) -> str:
        return (
            f"{self.presents_as}, {self.age_band}. {self.appearance} "
            f"Delivery: {self.delivery}. Voice: {', '.join(self.voice)}. "
            f"Speaks {self.language_text}."
        )

    def speaks(self, code: str) -> bool:
        return code in self.languages


@dataclass(frozen=True, slots=True)
class Query:
    """What the user typed, plus the one filter the product already has.

    Deliberately not a parsed spec. The whole premise is that a person can
    describe who they want in their own words and get relevant people back;
    turning that sentence into a form to fill in is the thing being replaced.
    """
    text: str
    kind: Kind | None = None       # None = the "All" tab
    limit: int = 24

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()
