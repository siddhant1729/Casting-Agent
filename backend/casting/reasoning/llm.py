"""The single seam where a model enters the pipeline.

Everything in stages 0-2 (models, catalog, cost, filters) must remain
importable without this module doing anything, and none of them import it.
That separation is the PRD's central bet: if the constraint and cost layers
are sound the rest is presentation, and if they are weak model output does not
rescue them.

Two implementations:

  GeminiClient  - real calls, used when GEMINI_API_KEY is present.
  NullClient    - returns nothing, so every caller must already have a
                  deterministic path. It is not a mock of Gemini; it is the
                  absence of a model, and the pipeline is required to work
                  under it.

`available` is surfaced all the way to the UI, because a shortlist produced
without a model is a different artefact from one produced with it and saying
so is cheaper than being caught.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Protocol

from ..env import load as load_env

MODEL = "gemini-3.5-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

#: Generous on purpose. This is a thinking model, and an identical trivial
#: prompt was measured between 2s and 39s on the same key within a minute. A
#: tight timeout does not fail loudly here — it silently drops to the word-
#: overlap fallback, and the screen just quietly gets worse.
TIMEOUT_SECONDS = 120

#: Scoring a profile against a description is a judgement, not a derivation.
#: Extended thinking buys nothing measurable here and costs the latency that
#: makes the surface feel broken.
THINKING_LEVEL = "low"

#: 429 and 503 from this endpoint are routinely transient — "spikes in demand
#: are usually temporary", in the API's own words. Retrying twice is the
#: difference between a degraded shortlist and a correct one.
RETRY_STATUSES = frozenset({429, 500, 503})
RETRIES = 2
BACKOFF_SECONDS = 2.0


class LLM(Protocol):
    available: bool
    #: Why the last call failed, or None. Surfaced by /api/health so a
    #: misconfiguration is distinguishable from having no key at all — the
    #: silent degrade is right for the user and useless for the operator.
    last_error: str | None

    def json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        """Return parsed JSON matching `schema`, or None if unavailable/failed.

        None is a normal outcome, not an error. Callers fall back."""


class NullClient:
    available = False
    last_error = None

    def json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        return None


class GeminiClient:
    available = True

    def __init__(self, api_key: str, model: str = MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self.last_error: str | None = None

    def _request(self, prompt: str, schema: dict[str, Any]) -> urllib.request.Request:
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.2,
                "thinkingConfig": {"thinkingLevel": THINKING_LEVEL},
            },
        }).encode()
        return urllib.request.Request(
            ENDPOINT.format(model=self._model),
            data=body,
            # The key travels in a header, never in the URL — query strings end
            # up in proxy and access logs.
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
        )

    @staticmethod
    def _extract(payload: dict[str, Any]) -> dict[str, Any] | None:
        """Pull the JSON answer out of the response.

        Parts are scanned rather than indexed: a thinking model may return a
        thought part alongside the answer, and `parts[0]` is only the text by
        convention, not by contract.
        """
        for candidate in payload.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if part.get("thought") or "text" not in part:
                    continue
                try:
                    parsed = json.loads(part["text"])
                except ValueError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
        return None

    def json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        """Return parsed JSON, or None. None is a normal outcome, not an error.

        Callers fall back to the deterministic path, so a failure here degrades
        the result rather than breaking the request. `last_error` records why,
        because a silent degrade is right for the user and useless for whoever
        has to work out why the ranking got worse.
        """
        for attempt in range(RETRIES + 1):
            try:
                with urllib.request.urlopen(
                    self._request(prompt, schema), timeout=TIMEOUT_SECONDS
                ) as response:
                    payload = json.loads(response.read())
            except urllib.error.HTTPError as error:
                self.last_error = f"HTTP {error.code}"
                if error.code in RETRY_STATUSES and attempt < RETRIES:
                    time.sleep(BACKOFF_SECONDS * (attempt + 1))
                    continue
                return None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                self.last_error = f"{type(error).__name__}: {error}"
                if attempt < RETRIES:
                    time.sleep(BACKOFF_SECONDS * (attempt + 1))
                    continue
                return None
            except ValueError as error:
                self.last_error = f"unparseable response: {error}"
                return None

            parsed = self._extract(payload)
            self.last_error = None if parsed is not None else "no JSON part in response"
            return parsed
        return None


#: Live clients, keyed by the configuration that produced them. Cached so
#: `last_error` survives between requests — a client built fresh per call would
#: always report None, which makes the health endpoint a decoration. A changed
#: key or model yields a different entry, so tests that swap the environment
#: still get the client they configured.
_clients: dict[tuple[str, str], "GeminiClient"] = {}


def get_client() -> LLM:
    """Gemini when a key is configured, the absence of a model otherwise.

    `.env` is read here rather than at import time, so a test or a caller can
    set the variable itself and still get the client it expects.
    """
    load_env()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip() or MODEL
    if not key:
        return NullClient()
    if (key, model) not in _clients:
        _clients[(key, model)] = GeminiClient(key, model)
    return _clients[(key, model)]
