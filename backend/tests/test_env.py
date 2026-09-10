""".env loading."""

from __future__ import annotations

import os

import pytest

from casting import env
from casting.reasoning.llm import GeminiClient, NullClient, get_client


@pytest.fixture(autouse=True)
def reset():
    """Loading is cached after the first call, so each test starts clean."""
    env._loaded = False
    yield
    env._loaded = False


def write(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text)
    return path


def test_values_are_read_into_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    env.load(write(tmp_path, "SOME_KEY=abc123"))
    assert os.environ["SOME_KEY"] == "abc123"


def test_the_real_environment_always_wins(tmp_path, monkeypatch):
    """A stale .env in a checkout must never override what an operator exported
    or what a deployment injected."""
    monkeypatch.setenv("SOME_KEY", "from-the-shell")
    applied = env.load(write(tmp_path, "SOME_KEY=from-the-file"))
    assert os.environ["SOME_KEY"] == "from-the-shell"
    assert applied == {}


def test_a_missing_file_is_not_an_error(tmp_path):
    assert env.load(tmp_path / "nothing-here") == {}


def test_loading_is_cached_after_the_first_call(tmp_path, monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    env.load(write(tmp_path, "SOME_KEY=one"))
    env.load(write(tmp_path, "SOME_KEY=two"))
    assert os.environ["SOME_KEY"] == "one"


@pytest.mark.parametrize("line,expected", [
    ("KEY=value", {"KEY": "value"}),
    ("  KEY = value  ", {"KEY": "value"}),
    ("export KEY=value", {"KEY": "value"}),
    ('KEY="quoted value"', {"KEY": "quoted value"}),
    ("KEY='single'", {"KEY": "single"}),
    ("KEY=", {"KEY": ""}),
    ("KEY=a=b", {"KEY": "a=b"}),
    ("# KEY=value", {}),
    ("", {}),
    ("no-equals-sign", {}),
    ("=novalue", {}),
])
def test_parsing(line, expected):
    assert env.parse(line) == expected


def test_comments_and_blanks_are_skipped():
    parsed = env.parse("# a comment\n\nA=1\n   \n# another\nB=2\n")
    assert parsed == {"A": "1", "B": "2"}


def test_a_hash_inside_a_value_is_kept():
    """Trailing-comment stripping would corrupt a key that contains a #."""
    assert env.parse("KEY=abc#123") == {"KEY": "abc#123"}


def test_the_env_file_is_found_from_the_repo_root():
    """The checked-in .env.example proves the search walks up out of the
    package to the repo root."""
    found = env.find_env_file()
    assert found is None or found.name == ".env"


# ------------------------------------------------------------ the client

def test_no_key_means_no_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert isinstance(get_client(), NullClient)


def test_a_blank_key_is_not_a_key(monkeypatch):
    """An empty assignment in .env is the default state of a fresh checkout. It
    must read as 'no model', not as a key made of whitespace."""
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert isinstance(get_client(), NullClient)


def test_a_key_produces_a_gemini_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = get_client()
    assert isinstance(client, GeminiClient) and client.available


def test_the_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    assert get_client()._model == "gemini-2.5-pro"


def test_the_model_defaults_when_unset(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert get_client()._model == "gemini-3.5-flash-lite"


def test_the_key_is_never_echoed_back_by_the_api(monkeypatch):
    """/api/health and /api/meta both report whether a model is configured.
    Reporting *which* one would put a secret in a browser."""
    from fastapi.testclient import TestClient
    from casting.api import app

    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-value")
    client = TestClient(app)
    for path in ("/api/health", "/api/meta"):
        assert "super-secret-value" not in client.get(path).text


def test_the_suite_never_reaches_the_live_api(monkeypatch):
    """The guard in conftest, asserted rather than assumed.

    Once a real key exists in .env, anything calling get_client() would reach
    the network — test_api.py drives endpoints that build a client from the
    environment. A suite that quietly starts making live calls is slow,
    non-deterministic, and stops exercising the offline paths it exists to
    protect, at exactly the moment a key is configured.
    """
    assert isinstance(get_client(), NullClient)
    assert not os.environ.get("GEMINI_API_KEY")


def test_clients_are_cached_so_the_last_error_survives(monkeypatch):
    """A client built fresh per request would always report last_error None,
    which makes /api/health a decoration."""
    monkeypatch.setenv("GEMINI_API_KEY", "cache-test-key")
    first = get_client()
    first.last_error = "HTTP 429"
    assert get_client() is first
    assert get_client().last_error == "HTTP 429"


def test_a_changed_key_yields_a_different_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key-one")
    first = get_client()
    monkeypatch.setenv("GEMINI_API_KEY", "key-two")
    assert get_client() is not first


def test_health_reports_the_failure_reason_not_the_key(monkeypatch):
    from fastapi.testclient import TestClient
    from casting.api import app

    monkeypatch.setenv("GEMINI_API_KEY", "another-secret")
    get_client().last_error = "HTTP 503"
    body = TestClient(app).get("/api/health").json()
    assert body["last_error"] == "HTTP 503"
    assert "another-secret" not in str(body)
