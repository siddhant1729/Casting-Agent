"""The HTTP surface. Thin layer, so these test the mapping, not the logic."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from casting.api import app
from casting.pipeline import EXAMPLE_QUERIES

client = TestClient(app)
QUERY = EXAMPLE_QUERIES[0]["text"]


@pytest.fixture(scope="module")
def results():
    return client.post("/api/search", json={"query": QUERY}).json()


def test_meta_carries_both_honesty_notices():
    """The UI cannot render the disclaimers if the API does not ship them, and
    hardcoding them in the frontend puts the claim where tests cannot reach."""
    meta = client.get("/api/meta").json()
    assert "Synthetic" in meta["catalog_notice"]
    assert "word overlap" in meta["scorer_notice"]
    assert len(meta["examples"]) == 3
    assert meta["kinds"] == ["human", "ai"]


def test_search_returns_everything_a_card_needs(results):
    item = results["items"][0]
    assert item["rank"] == 1
    assert item["actor"]["name"] and item["actor"]["delivery"]
    assert item["look"]["scene"] and item["look"]["wardrobe"]
    assert item["rationale"]["text"] and item["reservation"]["text"]
    assert 0 < item["match"]["score"] <= 1


def test_the_response_says_which_scorer_ran(results):
    assert results["scorer"] in {"model", "lexical"}
    assert results["model_used"] is False


def test_no_pricing_field_survives_anywhere_in_the_payload(results):
    """Usage is covered by membership. A rate leaking back into the API is a
    number the UI would eventually render."""
    blob = str(results)
    for gone in ("base_rate", "territory", "exclusivity", "budget", "cost", "₹"):
        assert gone not in blob, gone


def test_no_photoreal_portrait_is_ever_shipped(results):
    """The client gets a number to draw geometry from, never an image."""
    actor = results["items"][0]["actor"]
    assert isinstance(actor["portrait_seed"], int)
    assert not any(k in actor for k in ("portrait", "image", "photo", "url"))


def test_the_kind_tab_filters(results):
    ai = client.post("/api/search", json={"query": QUERY, "kind": "ai"}).json()
    assert {i["actor"]["kind"] for i in ai["items"]} == {"ai"}
    assert len(ai["items"]) < len(results["items"])


def test_an_unknown_kind_falls_back_to_all_rather_than_erroring():
    response = client.post("/api/search", json={"query": QUERY, "kind": "aliens"})
    assert response.status_code == 200
    assert response.json()["query"]["kind"] is None


def test_an_empty_query_is_a_valid_request_not_an_error():
    response = client.post("/api/search", json={"query": ""})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_the_limit_is_range_checked_at_the_edge():
    assert client.post("/api/search", json={"query": QUERY, "limit": 0}).status_code == 422
    assert client.post("/api/search", json={"query": QUERY, "limit": 500}).status_code == 422


def test_the_seed_is_echoed_so_the_screen_can_show_it(results):
    assert results["seed"] == 7
    other = client.post("/api/search", json={"query": QUERY, "seed": 23}).json()
    assert other["seed"] == 23
    assert [i["actor"]["id"] for i in other["items"]] != \
           [i["actor"]["id"] for i in results["items"]]


def test_health_reports_whether_a_model_is_configured():
    assert client.get("/api/health").json()["ok"] is True


# ------------------------------------------------- the comparison view

DESCRIPTION_QUERY = "warm, credible, explains money without sounding like a bank"


def test_name_search_returns_nothing_for_a_description():
    """The name lookup stays a name lookup.

    No performer is named "warm, credible, explains money...", so it returns
    nothing rather than quietly widening to the profile text. This is what makes
    the router's choice meaningful: the two searches answer different questions.
    """
    body = client.post("/api/actors", json={"query": DESCRIPTION_QUERY}).json()
    assert body["actors"] == []
    assert body["matched"] == 0
    assert body["roster_size"] == 45
    assert body["search_field"] == "name"


def test_a_description_is_routed_to_the_ranking():
    """Same words, same catalog, same seed — answered by the other path."""
    body = client.post("/api/search", json={"query": DESCRIPTION_QUERY}).json()
    assert body["items"]
    assert body["route"] == "description"
    assert body["actors"] == []


def test_name_search_finds_a_real_name():
    """It is a working search, not one rigged to fail."""
    body = client.post("/api/actors", json={"query": "priya"}).json()
    assert body["matched"] >= 1
    assert all("priya" in a["name"].lower() for a in body["actors"])


def test_name_search_is_case_insensitive():
    lower = client.post("/api/actors", json={"query": "priya"}).json()["matched"]
    upper = client.post("/api/actors", json={"query": "PRIYA"}).json()["matched"]
    assert lower == upper > 0


def test_name_search_does_not_match_on_profile_text():
    """Matching the delivery notes too would turn this into a weak version of
    the semantic search rather than the thing being compared against."""
    body = client.post("/api/actors", json={"query": "unhurried"}).json()
    assert body["matched"] == 0


def test_name_search_honours_the_kind_tab():
    body = client.post("/api/actors", json={"query": "", "kind": "ai", "limit": 100}).json()
    assert body["actors"] and {a["kind"] for a in body["actors"]} == {"ai"}


def test_an_empty_name_search_shows_the_whole_grid():
    """An empty search box is not a request for nothing."""
    body = client.post("/api/actors", json={"query": "", "limit": 100}).json()
    assert body["matched"] == body["roster_size"]


def test_name_search_carries_what_a_grid_card_needs():
    actor = client.post("/api/actors", json={"query": "priya"}).json()["actors"][0]
    assert actor["name"] and actor["look_count"] >= 1
    assert isinstance(actor["portrait_seed"], int)
    assert actor["kind"] in {"human", "ai"}


def test_name_search_ships_no_pricing_or_photo():
    actor = client.post("/api/actors", json={"query": "priya"}).json()["actors"][0]
    for gone in ("base_rate", "territory", "cost", "portrait", "image", "photo"):
        assert gone not in actor


# ------------------------------------------------------------------- CORS

def test_cors_allows_any_localhost_port():
    """Vite falls back to 5174 when 5173 is taken, and a fixed allowlist turns
    that into a browser CORS block that reads as "backend unreachable" while
    the API is running fine. Observed exactly that way."""
    for origin in ("http://localhost:5173", "http://localhost:5174",
                   "http://127.0.0.1:4173", "http://localhost:3000"):
        response = client.options(
            "/api/search",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200, origin
        assert response.headers.get("access-control-allow-origin") == origin


def test_cors_does_not_allow_arbitrary_remote_origins():
    response = client.options(
        "/api/search",
        headers={"Origin": "https://evil.example.com",
                 "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"


# --- Routing -----------------------------------------------------------------
#
# One box takes both kinds of query. Which search runs is decided on the server,
# and these pin the four answers it can give.


def test_a_name_is_routed_to_the_roster_lookup():
    body = client.post("/api/search", json={"query": "Rohan"}).json()
    assert body["route"] == "name"
    assert [a["name"] for a in body["actors"]] == ["Rohan K."]
    assert body["items"] == []


def test_a_full_name_routes_on_what_was_typed():
    """"Arjun B." is a name a user types, not two tokens to be split apart."""
    body = client.post("/api/search", json={"query": "Arjun B."}).json()
    assert body["route"] == "name"
    assert body["matched_names"] >= 1
    assert all("arjun" in a["name"].lower() for a in body["actors"])


def test_a_name_plus_a_description_runs_both():
    body = client.post(
        "/api/search",
        json={"query": "Rohan at a whiteboard, patient and authoritative"},
    ).json()
    assert body["route"] == "both"
    assert body["actors"] and body["items"]


def test_a_word_inside_a_name_is_not_a_name():
    """`search_by_name` is a substring match, so "man" reaches Manav.

    Routing on that would send "a man who explains things" to the name lookup on
    the strength of an article. Routing is on whole words in a name, so it does
    not.
    """
    body = client.post(
        "/api/search",
        json={"query": "a man who explains things without talking down"},
    ).json()
    assert body["route"] == "description"
    assert body["actors"] == []


def test_a_blank_query_routes_nowhere_rather_than_returning_the_whole_roster():
    """The name lookup returns the whole grid for a blank term — that is right
    for a grid with an empty search box, and wrong for this one box."""
    body = client.post("/api/search", json={"query": "  "}).json()
    assert body["route"] == "empty"
    assert body["actors"] == []
    assert body["items"] == []


def test_a_name_lookup_names_no_scorer():
    """Nothing was ranked, so claiming a scorer would be inventing one."""
    body = client.post("/api/search", json={"query": "Rohan"}).json()
    assert body["scorer"] == "none"
    assert body["model_used"] is False
