# PRD — Casting Agent

**Prototype for HexCoded**
Author: Siddhant Shaurya
Status: Draft — revised, see §11
Scope: Standalone prototype, proposed as a surface inside HexCoded

---

## 1. Summary

A casting tool that takes a description of the person you want, in plain language, and
returns a ranked list of **actor-looks** — each with the phrases from that performer's
profile that earned the match, and one stated reservation.

It replaces browsing with reading. The creative still chooses; the tool removes the part
where the roster is opaque until you have clicked through all of it.

---

## 2. Background

HexCoded's pitch is that you pick a real, licensed actor and get a finished video in
minutes. Casting is load-bearing — it is the step where the product's core differentiator
is actually exercised by the user.

The current **Pick an actor** surface is a grid of faces with a name search and a type
filter (All / AI actors / Human creators / My actors). Each card shows a portrait, a voice
indicator, and a count of available looks.

This is a competent browsing UI. It is the wrong shape for the decision being made.

### Observed gaps

**Search is name-matched, not meaning-matched.** The question in a creative's head is "who
reads as a credible, warm explainer for a fintech product in Hindi and English?" There is
no field that accepts that question. The search box accepts a name — which you can only
type if you already know the answer.

**Looks are a first-class concept that search cannot reach.** Actors carry multiple looks —
observed counts range from 2 to 5 — and they differ materially by setting: studio, home,
outdoor, classroom, beach, gym. A classroom look and a beach look are different casting
decisions with the same face. Today you find them by clicking into each actor
individually, which means the roster's real size is looks, not faces, and the grid shows
you the smaller number.

**Nothing on the card says how anyone reads.** Two faces tell you less than one sentence
about delivery. The information that decides the casting is the information the surface
does not carry.

### Framing

Casting is a retrieval problem where the query is a description and the corpus is people.
The current tool optimises for recognition — you scan faces until one looks right — which
works when you know the roster and fails completely when you do not. That is exactly the
position the primary user is in.

---

## 3. Users

**Primary — the small-agency creative or freelance content producer.**
Running several client campaigns at once. Does not know the roster. Cares about turnaround.
Cannot scan 45 faces and 138 looks to find the one warm explainer.

**Secondary — the in-house brand or content team member.**
Cares about consistency across a campaign, and about finding the same performer again in a
different setting.

**Non-user — the professional casting director.**
Has taste, relationships, and their own process. This tool is not aimed at them and should
not pretend to replace their judgment.

---

## 4. Goals

| # | Goal | How we know |
|---|------|-------------|
| G1 | Turn a plain-language description into a relevant, ordered list | User types a sentence and never touches a filter |
| G2 | Make every result checkable | Each card carries phrases quoted verbatim from that performer's own profile |
| G3 | Rank at look granularity, not actor granularity | The same actor appears with different looks at different ranks |
| G4 | Say what each result costs you | Exactly one stated reservation per candidate, derived from the record |
| G5 | Keep final creative judgment with the human | The tool ranks and explains; it never auto-selects |

### Non-goals

- Generating video. This sits before generation.
- Replacing casting taste.
- Modelling licensing, pricing, territories or usage terms. Membership covers usage; see §11.
- Managing contracts, payments, or actor onboarding.

---

## 5. User stories

**US-1** — As a creative, I describe the person I want in a sentence and get relevant
people back, without translating it into filters first.

**US-2** — As a creative, I can see *why* each result is there, in the performer's own
words rather than the tool's.

**US-3** — As a creative shooting an in-home demo, I get home-setting looks across the
whole roster in one view, not one actor at a time.

**US-4** — As a creative, I am told when someone is right but their looks are wrong, rather
than being quietly given a mismatch at rank one.

**US-5** — As a creative, I can narrow to human creators or AI actors, because that choice
is already part of how I think about the roster.

**US-6** — As a creative, I get one reservation per candidate, so I know what I am trading
off before I present it to a client.

---

## 6. Functional requirements

### 6.1 Query intake
- **FR-1** Accept free text. One sentence is enough; there is no minimum structure.
- **FR-2** Provide 3 seeded example queries. The first screen is never empty.
- **FR-3** No parsing into a form. The description *is* the query — turning a sentence into
  fields to fill in is the thing being replaced.
- **FR-4** Support the type filter the product already has (All / Human / AI). It is the
  only thing that ever removes a candidate.
- **FR-5** An empty query returns nothing, not the whole roster in arbitrary order.

### 6.2 Ranking
- **FR-6** Rank at look level. An actor may appear more than once with different looks.
- **FR-7** Score the person and the look together, so a right read in the wrong setting is
  a partial match rather than a false full one.
- **FR-8** Scoring is semantic. The catalog vocabulary and the query vocabulary are
  disjoint by construction, so a lexical scorer cannot reach a correct answer and the
  system cannot fake one.
- **FR-9** Candidates scoring zero are not returned. Padding a short list with irrelevant
  people is worse than a short list.
- **FR-10** Ranking never auto-selects. No default pick.
- **FR-11** Ordering is stable across identical runs and independent of roster order.

### 6.3 Evidence and explanation
- **FR-12** Each result carries up to three phrases justifying it, **quoted verbatim** from
  that candidate's own profile. A phrase not found in the source text is discarded rather
  than displayed.
- **FR-13** 2–3 sentence rationale per candidate, generated by slot-fill over cited record
  fields. Every claim resolves to a field; provenance is renderable.
- **FR-14** Exactly one reservation per candidate, **selected** from a closed set of
  structural facts — a language asked for and missing, a language only conversational, a
  setting asked for that this actor has no look for, the model's own stated caveat, a
  low-confidence score, a single look on file. `no material reservation` is a member of
  that set. Reservations are derived, never authored; a forced negative on a clean match is
  an invented one.

### 6.4 Degradation
- **FR-15** The pipeline runs with no model configured. It degrades to word overlap.
- **FR-16** The fallback is not propped up with a hand-written synonym table. Such a table
  would be a human drawing the semantic crossing by hand, which is the circularity the
  disjoint vocabularies exist to remove.
- **FR-17** The surface states which scorer produced the result being shown.
- **FR-18** A failed call, a rate limit, a malformed score, an unknown id, or an
  unquotable evidence phrase each degrade to something honest rather than erroring or
  inventing. Transient failures are retried before giving up.
- **FR-19** Scores within one result list come from one scorer. A partial model response
  falls back entirely rather than ranking model judgements against word counts.
- **FR-20** Failure is diagnosable. The health surface reports why the last model call
  failed, and never the key or the response.

### 6.5 Catalog integrity
- **FR-19** Catalog is synthetic, labelled as such in-product.
- **FR-20** Roster is regenerable from a user-visible seed.
- **FR-21** Actor and look descriptions are written in a vocabulary disjoint from the
  language queries are written in. Reseeding alone does not defeat the circularity
  objection — it resamples a distribution the author designed. Disjointness does: whatever
  the seed, the scorer never sees the words it is being searched with.
- **FR-22** No real person's likeness in any placeholder asset. Portraits are abstract
  geometry — generated photoreal faces can resemble real people, which is what this rule
  exists to prevent.

---

## 7. Experience

One screen.

**Search** → a text field that accepts a description, three seeded examples, and the
existing type tabs.

**Results** → look-level cards: abstract portrait, actor name, kind badge, look count, the
setting and scene, a fit score, the quoted evidence phrases, a rationale, and one
reservation.

The evidence chips get real design weight. They are the clearest signal that the system
read rather than retrieved, and they are the only part of the card a user can independently
check against the profile.

**Target demo path:** cold load → seeded query "someone warm and credible who can explain a
money app without talking down to anyone" → the top results are performers whose profiles
never use any of those words. Under 30 seconds, and the point lands without explanation.

---

## 8. Success criteria

Prototype-appropriate. No usage data exists, so these are qualitative and structural.

| Criterion | Bar |
|-----------|-----|
| Vocabulary disjointness | Enforced by test, on the banks and on generated output, across several seeds |
| Semantic necessity | The lexical fallback scores the planted "warm" actor at exactly 0.0 — proof the task cannot be solved lexically |
| Evidence integrity | Every displayed phrase verified present in the source profile; unverifiable ones dropped |
| Explanation quality | Every rationale claim traceable to a named record field; enforced by slot-fill, not by review |
| Robustness to data | Across ≥3 independent seeds: no seeded query returns an empty screen, and no rationale cites a field its record lacks |
| Honesty | README states what is real and what is stubbed, specifically |

Explicitly **not** claimed: casting accuracy, time saved, or any benchmark. No baseline
exists to measure against, and inventing one is the fastest way to lose the argument.

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Synthetic catalog reads as circular | High | Disjoint vocabularies, test-enforced in both directions. The scorer never sees the words it is searched with |
| Ranking is plausible-sounding model output rather than judgment | High | Evidence must be quoted verbatim from the profile and is verified before display. A card the user can check is a card that can be wrong in public |
| The real roster's profiles are too thin to rank on | Open | See §11. The ranking is only as good as the descriptions it reads |
| Offline behaviour looks broken | Medium | It is weak, deliberately, and says so on screen. Stated in README rather than hidden |
| Free-tier quota silently exhausts mid-demo | Medium | Measured, not assumed: 20 requests/day on `gemini-3.6-flash`. Default model chosen for usable limits; `/api/health` names the 429 so the failure is visible rather than mysterious |
| A face grid may be adequate at small roster sizes | Medium | The pitch rests on look-level granularity and on description search, which hold at any size — 45 actors are already 138 looks |

---

## 10. Build order

Dependency-ordered, not calendar-ordered.

**Stage 0 — Records and catalog.** Schema, the two disjoint vocabulary banks, seeded
generation, five planted cases. No AI.

**Stage 1 — Scoring.** The model scorer with batching and evidence verification, plus the
deliberately weak lexical fallback.

**Stage 2 — Explanation.** Rationale slot-fill with provenance; reservations selected from
the closed set.

**Stage 3 — Surface.** Search box, type tabs, result cards, honesty notices.

**Stage 4 — Evaluation and honesty pass.** The §8 bars across independent seeds. README
stating what is real and what is stubbed.

Stage 0 contains no AI and cannot import one. If the catalog and its vocabulary discipline
are sound, the rest is scoring and presentation. If they are weak, model output does not
rescue them — it just makes the circularity harder to see.

---

## 11. Revision note

This document previously specified a licensing layer: per-actor territory rates,
exclusivity holds against a campaign window, additive channel fees, sub-linear duration
curves, budget ceilings, itemised per-candidate cost, and a constraint solver with
counterfactual analysis of which constraint was binding.

It was built, tested, and then removed. Usage is covered by site membership, which makes
every one of those numbers an answer to a question the user does not have. An exclusions
panel explaining who was unaffordable is worse than no panel: it spends the most legible
part of the surface on a decision that was already made at signup.

What survived is what was about the person — look-level granularity, checkable evidence,
and one stated reservation. The vocabulary-disjointness argument, originally a defence of
the synthetic catalog, turned out to be the load-bearing idea once ranking became the whole
product.

Two requirements were also changed during implementation and are carried in their revised
form above: reservations are selected from a closed set rather than authored per candidate
(a mandatory written reservation forces an invention on a clean match), and the offline
fallback is left weak rather than bridged by an authored synonym table.

---

## 12. Open questions

**Q1 — What is the actual roster scale?** Not observable from outside. 45 actors is already
138 looks; the argument strengthens as the roster grows and does not depend on it.

**Q2 — Is "look" first-class in their data model, or an artifact of the UI?** The badge on
every card suggests first-class. Worth confirming, since the entire ranking unit rests on it.

**Q3 — How rich are the real profiles?** This is the question that decides whether any of
this survives contact with real data. Ranking is only as good as the descriptions it reads,
and a roster of two-word bios would need enriching before this earns its place. If profiles
do not exist, the proposal grows a second half: generate them, from the footage.

**Q4 — How does the existing automated casting work?** The homepage offers to "write it,
cast it and make the video for you", so casting already happens somewhere. If it is a
silent black box, this shifts from *adding search* to *making an existing choice legible
and steerable* — a stronger and smaller proposition.
