# Casting Agent

Describe the actor you want, in your own words. Get back the most relevant
**actor-looks** on the roster — each with the phrases from that performer's profile that
earned the match, and one thing it costs you.

It ranks and explains. It never picks.

Replaces browsing a grid of faces with a name search. Built against [`docs/PRD.md`](docs/PRD.md).

**New here?** [`docs/walkthrough.md`](docs/walkthrough.md) is the ten-minute
guided tour — what to type, what to look for, and how to break it on purpose.
This file is the reference underneath it.

---

## Running it

### Prerequisites

| | |
|---|---|
| **Python 3.12+** | What `pyproject.toml` declares. `StrEnum` is the hard floor (3.11). |
| **Node 20.19+ or 22.12+** | Vite 8's floor. `node --version` before you start. |
| **`GEMINI_API_KEY`** | Not required to run, but the product is only itself with it. Goes in `.env`. |
| `uv` | Optional. `run.sh` falls back to `venv` + `pip` when it is absent. |

### Quick start

```bash
cp .env.example .env        # then paste your Gemini key into it
./run.sh
```

Installs anything missing on first run, waits for the API to answer before starting the
UI, then stays in the foreground. Ctrl-C stops both. Override the ports with
`API_PORT=... UI_PORT=... ./run.sh`.

- **UI** — <http://localhost:5173>
  - `/` — brief in, ranked actor-looks out
  - `/compare` — the same query through the roster's name search and through this agent, side by side
- **API** — <http://localhost:8000>, docs at `/docs`

The brief box arrives pre-filled with a seeded example. Press **Rank actor-looks**.

### Setting up by hand

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt -e .   # -e . puts `casting` on the path
(cd frontend && npm install)
```

The `-e .` matters: it installs the package rather than the dependencies alone, so
`import casting` resolves from anywhere and neither pytest nor uvicorn needs a
`PYTHONPATH` in front of it.

### Running the pieces separately

```bash
.venv/bin/uvicorn casting.api:app --port 8000 --reload   # API only
(cd frontend && npm run dev)                             # UI only, expects the API on :8000
```

The UI reads its API base from `VITE_API`, so a backend elsewhere is
`VITE_API=http://127.0.0.1:9000 npm run dev`.

### Tests

```bash
.venv/bin/python -m pytest -q                                      # all 138
.venv/bin/python -m pytest backend/tests/reasoning -q              # scoring and explanation
.venv/bin/python -m pytest backend/tests/test_architecture.py -q   # the layer boundary
```

### The searches in a terminal

```bash
.venv/bin/python scripts/demo.py         # seed 7
.venv/bin/python scripts/demo.py 23      # any seed — the roster regenerates
```

Runs the three seeded example searches and prints the ranked results with their rationales.
No HTTP layer involved, so it also works as a smoke test when the frontend will not start.

### Configuration

Everything the app reads lives in `.env` at the repo root. `.env.example` is the committed
reference for what goes in it; `.env` itself is gitignored.

| Variable | Effect |
|---|---|
| `GEMINI_API_KEY` | Enables semantic ranking. Blank or absent falls back to word overlap. Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.5-flash-lite` — read the note below before changing it. |
| `VITE_API` | Frontend only, and read at build time — passed on the command line locally, set by `render.yaml` on a deploy. Defaults to `http://127.0.0.1:8000`. |
| `ALLOWED_ORIGINS` | Deployment only. Comma-separated origins allowed to call the API. Localhost and `*.onrender.com` are already allowed. |
| `FRONTEND_DIST` | Deployment only. Overrides where the API looks for a built frontend to serve itself. |

Loading is `casting/env.py`, about forty lines of standard library rather than
`python-dotenv` — reading `KEY=value` does not justify a dependency, and the requirements
files stay honest about covering only the HTTP surface.

#### Choosing a model

The default is `gemini-3.5-flash-lite`, chosen against the live API rather than from a spec
sheet. Two findings decided it:

**Free-tier quota is per model, per day, and small.** `gemini-3.6-flash` allows **20
requests per day**. At three batched calls per search that is roughly six searches before
the key stops working — and it does not stop loudly. Every batch 429s, ranking falls back
to word overlap, and the screen quietly gets worse. The lite models have usable limits.

**Latency is the other half.** The same trivial prompt against `gemini-3.6-flash` was
measured between 2s and 39s within a minute. `gemini-3.5-flash-lite` returns a full
138-candidate search in **8–11 seconds**, with no loss of ranking quality on the seeded
queries — the planted "warm without the word warm" actor still comes back first at 95%.

Concurrency is capped at three in-flight batches. Ten returned 429 on all ten.

**A variable already in your shell always wins over `.env`.** A stale file in a checkout,
or one committed by accident, must never silently override what an operator exported or
what a deployment injected. `test_the_real_environment_always_wins` holds that.

### The fallback is weak on purpose

With no `GEMINI_API_KEY`, ranking falls back to word overlap. It will visibly miss people
it should find, and that is the point rather than a defect — see *The vocabulary gap*
below. The UI says which scorer produced what you are looking at, in the masthead notices.

### When it does not start

| Symptom | Cause |
|---|---|
| UI says it can't reach the API | It retries on its own every 2s, and there is a **Retry now** button. If it persists: `curl localhost:8000/api/health`. |
| `Port 5173 is already in use` | A stale dev server. `run.sh` now refuses to start rather than letting Vite drift to another port — stop it, or run `UI_PORT=5175 ./run.sh`. |
| `ModuleNotFoundError: casting` | The editable install did not run. `.venv/bin/pip install -e .` |
| `No module named pytest` after it worked before | The venv was emptied. `.venv/bin/pip install -r requirements-dev.txt -e .` rebuilds it. |
| Vite refuses to start | Node below 20.19. |
| Ranking still says *word overlap* after adding a key | `curl localhost:8000/api/health` — it reports `model_available` and `last_error`. `HTTP 429` means the daily quota is spent; `HTTP 404` means the model id is retired. |
| Searches return nothing sensible | No API key. That is the word-overlap fallback, working as described. |

---

## Deploying to Render

`render.yaml` is a blueprint: **New > Blueprint** in the Render dashboard,
point it at this repo, and it creates two services.

| Service | What it is | URL |
| --- | --- | --- |
| `casting-agent-api` | Python web service, `uvicorn casting.api:app` | `…-api.onrender.com` |
| `casting-agent-web` | Static site, the Vite build | `…-web.onrender.com` — open this one |

Set `GEMINI_API_KEY` on the API service in the dashboard. It is marked
`sync: false` so the key is never committed. Without it the deploy still
succeeds and ranking falls back to word overlap, which `/api/health` reports.

Three things in `api.py` exist for this and nothing else:

* **`ALLOWED_ORIGINS`** — the browser now calls the API cross-origin, so the
  frontend's URL has to be allowed. `*.onrender.com` is matched by default, so
  this is only needed for a custom domain.
* **`$PORT` and `--host 0.0.0.0`** — Render assigns the port and routes to it.
  Binding loopback makes the service unreachable and the health check fail.
* **`env.load()` at import** — the dashboard's variables are already in the
  environment and win over any `.env`, so this is a no-op there. It is what
  lets a bare `uvicorn casting.api:app` see `.env` locally.

Free instances sleep after inactivity; the first request after that takes
roughly thirty seconds while the container starts.

### One service instead of two

If `frontend/dist` exists, the API serves the UI from its own origin and there
is no cross-origin surface at all. Build the frontend during the API's build
step and drop the static site:

    buildCommand: pip install -r requirements.txt && pip install -e . && cd frontend && npm ci && npm run build

Client-side routes are handled — `/compare` returns `index.html` rather than a
404, on both layouts.

---

## The vocabulary gap

This is the idea the whole thing rests on, and the reason the tests are shaped the way
they are.

The roster is written in a casting vocabulary that shares **no words** with the language
people search in. A user types *warm*, *credible*, *authoritative*. A profile says
*"unhurried, with the vowels of somebody's older cousin, explains without condescending"*.

`test_vocabulary_banks_are_disjoint` fails the build if those two banks ever overlap, and
`test_generated_profiles_never_use_query_vocabulary` holds it on generated output across
several seeds.

Two things follow.

**A string match scores zero.** Bridging that gap requires reading for meaning, so the
product cannot fake a good result with substring matching. `test_the_lexical_fallback_cannot_bridge_the_vocabulary_gap`
pins this: the planted actor written to answer "someone warm" scores exactly 0.0 under
word overlap.

**The synthetic catalog stops being circular.** The usual objection to a made-up roster is
that the matcher is being graded against data its own author wrote. Reseeding does not
answer that — a new seed resamples a distribution the author designed. Disjoint
vocabularies do: whatever the seed, the scorer never sees the words it is being searched
with.

The honest remaining gap is that a human chose both vocabularies, so the *difficulty* of
the crossing is authored even though the crossing itself is not.

---

## What is real and what is stubbed

### Real

| | |
|---|---|
| **Look-level ranking** | The unit is the actor-look, not the actor. One performer appears at several ranks with different looks, and the scorer sees the person and the room together, so a right read in the wrong setting is a partial match rather than a false full one. |
| **Model scoring** | Gemini reads the description and each profile, returns a fit score and the phrases that justify it. Batched, not one call per candidate. |
| **Evidence is quoted, not generated** | Every phrase on a card is verified to appear verbatim in that candidate's own profile text before it is shown. A phrase the model wrote itself is discarded — it is a claim about the record rather than a citation of it, and those are the ones that turn out to be flattering and false. |
| **Rationale provenance** | Every sentence carries the record fields it was built from, and `resolve_citation` walks each path back to a live value. A sentence citing a field that does not exist fails a test rather than shipping. |
| **Reservations** | Selected from a closed set of six structural facts plus "no material reservation". Derived, never authored. |
| **Graceful degradation** | A missing key, a failed call, a rate limit, a malformed score, an unknown id, or an unquotable evidence phrase each degrade to something honest instead of erroring or inventing. Transient 429/503 responses are retried with backoff first. |
| **One scale per list** | If the model does not score *every* candidate, the whole search falls back to word overlap rather than mixing scorers. A 0.95 judgement ranked against a 0.20 word count is a list sorted by two incompatible numbers — observed live, where partial model output let word-overlap noise out-rank genuine matches. |
| **Diagnosable failure** | `/api/health` reports *why* the last call failed — `HTTP 429`, `HTTP 404` — never the key or the response. A silent degrade is right for the user and useless for whoever has to work out why the ranking got worse. |
| **Comparison is computed, not staged** | `/compare` runs both searches against the same catalog and seed. The left panel's empty result is real: `POST /api/actors` matches on name only, and nobody is *named* "warm, credible, explains money without sounding like a bank". Staging that would make the comparison a claim rather than a demonstration. |
| **Hermetic tests** | The suite never reaches the live API, even with a real key in `.env`. Guarded at session scope, because a module-scoped fixture is set up before function-scoped ones and slipped through the first version of the guard. |

### Stubbed or weak

**The catalog is synthetic.** 45 actors, 138 looks, regenerated from a visible seed. Five
planted actors are identical under every seed so the hard cases do not depend on the RNG
obliging: someone warm whose profile never says *warm*, someone whose read is the exact
opposite, the right person with no classroom look, the classroom look on the wrong person,
and a single-look AI actor.

**Portraits are abstract geometry**, drawn from a deterministic per-actor seed. Not a
stylistic choice — generated photoreal faces can resemble real people, which is precisely
what a placeholder must not do.

**The offline scorer is word overlap** and is meant to be poor. It could be propped up
with a hand-written synonym table, but that table would be a human drawing the semantic
crossing by hand — the exact circularity the disjoint vocabularies exist to remove.

### Not claimed

Casting accuracy, time saved, or any benchmark. No baseline exists to measure against.

---

## Architecture

```
description ─▶ search ─▶ explain ─▶ ranked looks
               (LLM)     (pure)
```

```
README.md                     this file
docs/PRD.md                   the spec this was built against
docs/walkthrough.md           the guided tour of the running app
render.yaml                   Render blueprint — API service + static frontend
.env.example                  committed reference; copy to .env
run.sh                        sets up and starts both servers
requirements.txt              API runtime deps (the pipeline needs none)
requirements-dev.txt          the above, plus pytest and httpx

backend/casting/
  env.py                      .env loading, stdlib only
  domain/                     records and the catalog. No AI, no network.
    models.py                 Actor, Look, Query, and the searchable profile text
    vocab.py                  the two disjoint word banks
    catalog.py                seeded roster + five planted cases
  reasoning/                  the only layer allowed a model
    llm.py                    the single seam
    search.py                 model scorer + the honest lexical fallback
    explain.py                rationale slot-fill + reservation selection
  pipeline.py                 orchestration and the seeded examples
  serialize.py                record -> JSON
  api.py                      FastAPI surface

backend/tests/                138 tests, mirroring the layers
  test_architecture.py        enforces the boundary above
scripts/demo.py               the seeded searches in a terminal

design/                       the Stitch export the UI was built against
  casting-screen.png          full-resolution screen (2560x3574)
  casting-screen.html         source of the palette and type scale

frontend/src/
  App.tsx                     shell, hero, route tabs
  pages/Casting.tsx           brief + ranked actor-looks
  pages/Compare.tsx           name search vs semantic search, one query
  components/                 Sidebar, Topbar, LookCard, Portrait, Notices
  lib/                        api client + types mirroring serialize.py
```

`domain` contains no AI and cannot import one — `test_architecture.py` fails the build if
it does, and also fails if anything outside `llm.py` reaches an inference endpoint. A
catalog that can see the scorer is a catalog that can be shaped to flatter it, which is the
circularity objection arriving through the back door.

Ranking happens entirely on the server. The browser never re-scores or re-sorts, because a
second ordering implemented in TypeScript is a second thing to keep true.

---

## The interface

Built against the Stitch export in `design/`, which is committed so a checkout can be
reviewed against the reference. Colours and type are taken from that file's own Tailwind
config rather than sampled off a screenshot: Inter and Plus Jakarta Sans, brand green
`#00b67a`, page `#f7f9f8`.

The sidebar reproduces HexCoded's, with **Casting sitting directly below Actors** — that
placement is the argument the prototype is making. Every other nav item is inert: dimmed,
`pointer-events: none`, unfocusable, announced as disabled. They mark the surrounding
product. A nav item that looks live and goes nowhere is worse than one that plainly does
not.

### The ranking unit is a look, not an actor

The same performer appears several times with different looks at different ranks. On the
seeded brief that is 24 cards from 13 actors, 8 of whom appear more than once.
Deduplicating by actor would collapse the entire premise — a kitchen look and a beach look
are different casting decisions with the same face.

### Three deliberate departures from the design

**Look labels.** The export shows coined titles like *"FinTech Anchor / Everyday Trust"*.
Nothing in the payload supports those, so cards carry the record's own `setting · scene`.
An invented creative label is a claim the API does not make.

**Portraits.** The export uses photographs of real people. The catalog is synthetic, and a
*generated* photoreal face can resemble a real person, so abstract marks stay.

**Rationale length.** The API returns three provenance-carrying sentences; cards render the
first two. The third is demographics, already on screen as tags. Nothing is reworded in the
browser — the sentences are slot-filled server-side over cited record fields, and rewriting
them client-side would break that guarantee silently.

### What the design specifies and this does not build

Two of the export's five regions need a backend that does not exist here:

| In the design | Needs |
|---|---|
| Region 2 — *"What we understood"*, editable attribute chips with `— Empty` slots | a brief parser and a typed spec with unset fields |
| Tonal risk slider | a re-rank parameter |
| *"12 looks not shown"* | language/setting filtering with per-look reasons |
| *"Diagnostic & empty-state recovery engine"* | counterfactual recounts |

All four were removed when the product narrowed to description search. The zero-result
state here names the roster size, the scorer that ran, and what would change the outcome —
honest, but thinner than the counterfactual panel the design draws.

---

## What was removed, and why

An earlier version of this modelled licensing: per-actor territory rates, exclusivity
holds, channel and duration curves, budget ceilings, an itemised cost per candidate, and a
constraint solver with counterfactual "what would relaxing this return" analysis.

All of it is gone. Usage is covered by site membership, so pricing a decision that has
already been paid for put a number on every card that the user had no decision to make
about — and an exclusions panel explaining who was unaffordable was answering a question
nobody had asked. `test_no_pricing_field_survives_anywhere_in_the_payload` keeps it from
creeping back.

What survived the cut is what was about the *person*: look-level granularity, evidence you
can check, and one stated reservation per candidate.

---

## Open questions

Carried from [`docs/PRD.md`](docs/PRD.md): the real roster scale, whether "look" is
first-class in the underlying data model or an artifact of the UI, and how much of a
performer's profile actually exists to be searched. The last one decides how much of this
survives contact with real data — the ranking is only as good as the descriptions it reads,
and a roster of two-word bios would need enriching before any of this earns its place.
