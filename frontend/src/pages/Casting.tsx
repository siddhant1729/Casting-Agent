import { useCallback, useEffect, useRef, useState } from "react";
import { LookCard } from "../components/LookCard";
import { Notices } from "../components/Notices";
import { search } from "../lib/api";
import type { Meta, Results } from "../lib/types";

// Region 1 (the brief) and Region 3 (ranked actor-looks) from the design.
//
// Region 2 ("what we understood" — editable attribute chips) and the tonal-risk
// slider are not built. They need a brief parser, a typed spec with unset
// fields, and a re-rank parameter, none of which exist in the API this is
// wired to. Rendering chips that cannot round-trip, or a slider that changes
// nothing, would be a picture of a feature rather than the feature.

export function Casting({ meta }: { meta: Meta }) {
  const [query, setQuery] = useState(meta.examples[0]?.text ?? "");
  const [results, setResults] = useState<Results | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef(0);

  const run = useCallback(async (text: string) => {
    const ticket = ++pending.current;
    setBusy(true);
    setError(null);
    try {
      const next = await search(text, null, meta.default_seed);
      if (ticket === pending.current) setResults(next);
    } catch (e) {
      if (ticket === pending.current) setError(String(e));
    } finally {
      if (ticket === pending.current) setBusy(false);
    }
  }, [meta.default_seed]);

  useEffect(() => {
    if (meta.examples[0]) run(meta.examples[0].text);
  }, [meta, run]);

  return (
    <>
      <section className="region" aria-labelledby="region-brief">
        <div className="region-head">
          <span className="region-title" id="region-brief">
            Region 1 · Campaign brief
          </span>
          <span className="pill">Describe who you need, in your own words</span>
        </div>

        <label className="sr-only" htmlFor="brief">Campaign brief</label>
        <textarea
          id="brief"
          className="brief"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(query);
          }}
          placeholder="e.g. someone warm and credible who can explain a money app without talking down to anyone"
        />

        <div className="presets">
          <span className="presets-label">Quick brief presets:</span>
          {meta.examples.map((example) => (
            <button
              key={example.label}
              className="preset"
              onClick={() => {
                setQuery(example.text);
                run(example.text);
              }}
            >
              {example.label}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 18, display: "flex", gap: 12, alignItems: "center" }}>
          <button className="btn" disabled={busy} onClick={() => run(query)}>
            {busy ? "Ranking…" : "Rank actor-looks"}
          </button>
          {busy && <span className="spinner-note">scoring every look against your brief…</span>}
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      {results && (
        <section className="region" aria-labelledby="region-ranked">
          <div className="region-head">
            <span className="region-title" id="region-ranked">
              Region 3 · Ranked actor-looks
              <span className="region-note">
                {" "}(Ranked unit is an actor-look, not an actor. No pricing or booking locks.)
              </span>
            </span>
            <span className="region-note">Semantic affinity score</span>
          </div>

          {results.items.length === 0 ? (
            <ZeroState results={results} />
          ) : (
            <div className="looks">
              {results.items.map((item) => (
                <LookCard key={`${item.actor.id}-${item.look.id}`} item={item} />
              ))}
            </div>
          )}

          <Notices results={results} scorerNote={meta.scorer_notice} />
        </section>
      )}
    </>
  );
}

// Never a blank panel. Without a constraint layer there is no filter to name,
// so this states what was actually searched and what would change the outcome,
// rather than implying a filter that does not exist.
function ZeroState({ results }: { results: Results }) {
  const blank = !results.query.text.trim();
  return (
    <div className="empty-state">
      <strong>
        {blank ? "Describe who you are looking for" : "0 looks match this brief"}
      </strong>
      {blank ? (
        "The roster is searched on your description — an empty brief has nothing to rank against."
      ) : (
        <>
          All {results.look_count} looks across {results.roster_size} actors were scored;
          none scored above zero.
          <span className="why">
            {results.model_used
              ? "Ranking ran on the model path. Broaden the description — naming a setting or a language gives it more to match on."
              : "Ranking fell back to word overlap, which only matches literal words. A GEMINI_API_KEY enables semantic matching and will return results for this brief."}
          </span>
        </>
      )}
    </div>
  );
}
