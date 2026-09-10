# Walkthrough

A guided tour of the running app: what to do, in order, and what each step is
meant to show. Roughly ten minutes.

[`../README.md`](../README.md) is the reference — setup, configuration, every
flag. [`PRD.md`](PRD.md) is the spec this was built against. This file is
neither: it is the demo, written down.

**Set `GEMINI_API_KEY` before you start.** Without it the app runs, but it runs
the word-overlap fallback, and step 2 is the one thing here that does not work
without a model. Step 6 is where you turn it off on purpose.

```bash
cp .env.example .env        # paste your key
./run.sh                    # http://localhost:5173
```

---

## 1. The brief, not the filters

Open <http://localhost:5173>. The brief box arrives pre-filled with the seeded
example:

> Someone warm and credible who can explain a money app without talking down to
> anyone. Should feel like a person you'd actually ask.

Read it as a sentence a person would actually say to a colleague. There is no
age dropdown, no tone slider, no faceted sidebar — the whole input is prose.
That is the argument: the roster is opaque until you have clicked through all of
it, and a filter panel only helps if you already know what you are filtering
for.

Press **Rank actor-looks**. Eight to eleven seconds — the model reads all 138
candidates in batches.

---

## 2. The result that a keyword search cannot reach

**Priya M. comes back first, at 95%.**

Now open her card and read the evidence phrases:

> "laugh lines that arrive before the laugh", "explains without condescending"

The word *warm* does not appear. Nor does *credible*, *approachable*, or
*reassuring*. Her profile never uses any of them — and neither does anybody
else's, because the catalog and the query vocabulary are two **disjoint word
banks**, enforced by `test_vocabulary_banks_are_disjoint`.

This is the single thing worth checking in the whole tour. A substring matcher
scores this record **exactly 0.0**, and there is a test pinning that number.
Ranking her first requires reading for meaning; nothing about the result can be
explained by literal overlap.

**Also check what is *not* there.** Arjun T. is written as the opposite read —
*"clipped, almost impatient, declarative, sells nothing"* — and a scorer
matching on surface features like "Indian name, mid-30s, native Hindi" would
happily return him for a warmth query. He does not appear.

### The evidence is quoted, not written

Every phrase on a card is checked against that candidate's own profile text
before it is displayed. If the model writes a phrase that is not verbatim in the
record, it is discarded rather than shown. The phrases that turn out to be
flattering and false are exactly the ones a model invents, so the card can only
cite; it cannot characterise.

---

## 3. The same face, several times

Scroll. Priya appears again lower down with her **studio** look. On the seeded
brief the list is 24 cards drawn from 13 actors, 8 of them more than once.

That is deliberate and it is the product's unit of work. A kitchen counter in
afternoon light and a seamless grey studio are two different casting decisions
with the same person in them, and the scorer sees the person and the room
together — so the right read in the wrong room scores as a partial match rather
than a false full one. Deduplicating by actor would collapse the premise.

---

## 4. What it costs you

Every card carries exactly one **reservation**, and they are selected from a
closed set of six structural facts about the record plus *"no material
reservation"*. Never authored, never generated.

Run the second example to see one bite. Pick **Teacher, on camera**:

> A teacher type at a whiteboard — patient, authoritative, comfortable with a
> class in front of them. Hindi and Tamil.

The top result carries:

> Tamil is conversational, not native — worth a read test before committing a
> whole shoot to it.

That is read off the language map, not decided by a model. The generic one —
*"Nothing on the record argues against them, which is not the same as saying
they are right for it"* — is the honest form of no reservation, and it is
phrased that way on purpose: silence about risk is not evidence of its absence.

### The two planted teacher cases

This query exists to make the person/room split visible.

| | On the record | What should happen |
|---|---|---|
| **Devika R.** | Delivery answers the query exactly — *"talks you through it the way a colleague would"*. No classroom look at all. | Ranks on her read, and the card says which room you are actually getting. |
| **Rohan K.** | Has the classroom — whiteboard half-wiped, marker in hand. Reads nothing like a teacher: *"conversational to the point of rambling"*. | The setting is a real match; the person is not, and the score should not pretend otherwise. |

Neither is simply right. Both are the kind of near-miss a grid of faces hides
and a ranked list has to state.

---

## 5. The comparison, computed live

Open **`/compare`**. The same query runs through the roster's existing name
search on the left and through this agent on the right.

The left panel comes back **empty**, and that is the real result rather than a
staged one: `POST /api/actors` matches on name, and nobody is *named* "warm,
credible, explains money without sounding like a bank". The panel says
`search_field: name` so the UI never has to guess why it is empty.

Staging that would turn the comparison into a claim. Running both against the
same catalog and the same seed keeps it a demonstration.

---

## 6. Break it on purpose

Worth five minutes, because how it fails is most of what is being proposed here.

**Take the key away.** Comment out `GEMINI_API_KEY` in `.env` and restart.
Search again: the masthead notice now says ranking fell back to **word
overlap**, and the results get visibly worse — Priya drops out entirely. The
fallback is weak by design. Propping it up with a synonym table would be a human
drawing the semantic crossing by hand, which is the circularity the disjoint
vocabularies exist to remove.

**Ask why.** `curl localhost:8000/api/health` reports `model_available` and
`last_error` — `HTTP 429` for a spent daily quota, `HTTP 404` for a retired
model id. It reports the *reason*, never the key and never the model's
response. A silent degrade is right for the user and useless for whoever has to
work out why the ranking got worse.

**Change the seed.** The roster regenerates from it; the five planted actors are
identical under every seed, so the hard cases never depend on the RNG obliging.

```bash
.venv/bin/python scripts/demo.py 23
```

**Search for something nobody is.** The zero-result state names the roster size,
the scorer that ran, and what would change the outcome.

---

## 7. Reading the code, in the order it runs

```
description ─▶ search ─▶ explain ─▶ ranked looks
               (LLM)     (pure)
```

| Step | File | What to look for |
|---|---|---|
| 1 | `backend/casting/api.py` | Thin on purpose. Maps a request onto the pipeline and makes no decisions. |
| 2 | `pipeline.py` | Orchestration and the seeded examples. |
| 3 | `domain/catalog.py` | The roster, and the five planted actors at the top with a comment each saying what they are for. |
| 4 | `domain/vocab.py` | The two disjoint word banks. The whole premise is these two lists. |
| 5 | `reasoning/search.py` | Model scorer plus the lexical fallback. Note that a partial model result falls back **entirely** rather than mixing scorers — a 0.95 judgement ranked against a 0.20 word count is a list sorted by two incompatible numbers. |
| 6 | `reasoning/explain.py` | Rationale slot-fill over cited record fields, and reservation selection from the closed set. |
| 7 | `backend/tests/test_architecture.py` | The layer boundary, enforced: `domain` cannot import a model, and nothing outside `llm.py` may reach an inference endpoint. |

The last one is the load-bearing test. A catalog that can see the scorer is a
catalog that can be shaped to flatter it — the circularity objection arriving
through the back door.

```bash
.venv/bin/python -m pytest -q      # 138, none of which touch the live API
```

The suite is hermetic even with a real key in `.env`, guarded at session scope.

---

## 8. What you should not conclude

No casting accuracy is claimed, no time saved, no benchmark. There is no
baseline to measure against, and the catalog is synthetic.

What the tour is meant to establish is narrower: that the ranking crosses a
vocabulary gap a string match cannot, that every phrase shown is quoted from the
record rather than written about it, and that each failure mode degrades to
something honest. Whether that survives contact with a real roster depends on
how much of a real performer's profile exists to be read — the open question
carried from [`PRD.md`](PRD.md), and the one that decides how much of this is
worth keeping.
