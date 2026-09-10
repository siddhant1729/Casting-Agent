"""Test-wide guarantees.

The suite must be hermetic. Once a real `GEMINI_API_KEY` exists in `.env` — and
on a working checkout it does — anything calling `get_client()` would otherwise
reach the live API: `test_api.py` drives the real endpoints, and those endpoints
build a client from the environment.

That would make the suite slow, network-dependent, non-deterministic, and
quietly expensive. Worse, it would make the offline-fallback tests assert
against model output, so the paths they exist to protect would stop being
exercised at exactly the moment a key is configured.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _seal_the_session():
    """Close the door before any fixture of any scope opens.

    The function-scoped guard below is not sufficient on its own: a
    module-scoped or session-scoped fixture is set up *before* function-scoped
    autouse fixtures run, so `test_api.py`'s module-scoped fixture escaped it
    and made a live call — an eight-second setup that only showed up in
    --durations. Scope ordering is the kind of hole that hides in a green suite.
    """
    patch = pytest.MonkeyPatch()
    patch.setattr("casting.reasoning.llm.load_env", lambda *a, **k: {})
    patch.setenv("GEMINI_API_KEY", "")
    yield
    patch.undo()


@pytest.fixture(autouse=True)
def no_live_model_calls(monkeypatch):
    """Every test runs as if no key were configured.

    Blanking the variable is not enough on its own: an empty value is falsy, so
    `env.load` treats it as unset and refills it from `.env`. The loader called
    by `get_client` is stubbed out as well, which is the part that actually
    closes the door.

    `casting.env` itself is left alone so `test_env.py` can exercise the real
    parser and loader against temporary files.

    Tests needing model behaviour inject a stub client explicitly — a stub you
    can read beats a live call you cannot reproduce.

    This one re-applies per test, so a test that legitimately sets a key (the
    ones in `test_env.py`) cannot leak it into the next.
    """
    monkeypatch.setattr("casting.reasoning.llm.load_env", lambda *a, **k: {})
    monkeypatch.setenv("GEMINI_API_KEY", "")
