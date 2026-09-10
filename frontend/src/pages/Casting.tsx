import { useCallback, useEffect, useRef, useState } from "react";
import { LookCard } from "../components/LookCard";
import { Notices } from "../components/Notices";
import { Portrait } from "../components/Portrait";
import { search } from "../lib/api";
import type { Meta, Results } from "../lib/types";

// One box, both searches.
//
// A name off the roster and a description of a person arrive through the same
// input, and the server decides which search answers — the response carries a
// `route` saying which ran. Nothing here inspects the query to guess: a second
// copy of that decision in TypeScript is a second thing to keep true, and it
// would drift the first time the rule changed.
//
// The brief's editable attribute chips and tonal-risk slider are not built.
// They need a brief parser, a typed spec with unset fields, and a re-rank
// parameter, none of which exist in the API this is wired to.

// What produced what is on screen, in the plainest words available.
const PATH_NOTE: Record<string, string> = {
  name: "Matched on name.",
  description: "Ranked on your description.",
  both: "Ranked on your description.",
};

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

  const named = results?.actors ?? [];
  const ranked = results?.items ?? [];
  const nothing = results && named.length === 0 && ranked.length === 0;

  return (
    <>
      <section className="region" aria-labelledby="region-brief">
        <div className="region-head">
          <span className="region-title" id="region-brief">
            Who are you looking for?
          </span>
          <span className="pill">In your own words</span>
        </div>

        <label className="sr-only" htmlFor="brief">Who are you looking for?</label>
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
        <p className="input-note">Names or descriptions — either works.</p>

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
            {busy ? "Searching…" : "Find matches"}
          </button>
          {busy && <span className="spinner-note">searching the roster…</span>}
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      {results && (
        <section className="region" aria-labelledby="region-results">
          <div className="region-head">
            <span className="region-title" id="region-results">
              {named.length > 0 && ranked.length === 0 ? "Performers" : "Matches"}
            </span>
            <span className="region-note">{PATH_NOTE[results.route] ?? ""}</span>
          </div>

          {nothing ? (
            <ZeroState results={results} />
          ) : (
            <>
              {named.length > 0 && (
                <>
                  <p className="path-note">
                    {named.length} {named.length === 1 ? "performer" : "performers"} on
                    the roster {named.length === 1 ? "is" : "are"} named “{results.query.text}”.
                  </p>
                  <div className="grid-actors">
                    {named.map((actor) => (
                      <div className="grid-actor" key={actor.id}>
                        <Portrait seed={actor.portrait_seed} size={96} />
                        <div className="name">{actor.name}</div>
                        <div className="meta">{actor.look_count} looks · {actor.kind}</div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Both halves answered. The divider says the list below is a
                  different question being answered, not more of the same one. */}
              {named.length > 0 && ranked.length > 0 && (
                <div className="divider">
                  <span>and looks that fit the rest of what you typed</span>
                </div>
              )}

              {ranked.length > 0 && (
                <div className="looks">
                  {ranked.map((item) => (
                    <LookCard key={`${item.actor.id}-${item.look.id}`} item={item} />
                  ))}
                </div>
              )}
            </>
          )}

          <p className="region-note" style={{ marginTop: 14 }}>
            Placeholder art — no generated faces.
          </p>

          {/* The ranking chips describe a scorer. A name lookup never ran one,
              so on that path there is nothing honest for them to report. */}
          {results.route !== "name" && (
            <Notices results={results} scorerNote={meta.scorer_notice} />
          )}
        </section>
      )}
    </>
  );
}

// Never a blank panel. It says what was actually searched, and points at the
// other kind of query — the box takes both, and a miss is usually a person
// reaching for the one they did not type.
function ZeroState({ results }: { results: Results }) {
  const blank = !results.query.text.trim();
  return (
    <div className="empty-state">
      <strong>
        {blank ? "Type a name or describe who you need" : "Nothing matched"}
      </strong>
      {blank ? (
        "An empty box has nothing to search on."
      ) : (
        <>
          No performer is named “{results.query.text}”, and all {results.look_count} looks
          across {results.roster_size} actors were scored without one rising above zero.
          <span className="why">
            {results.model_used
              ? "Try a performer's name, or describe the read you want — naming a setting or a language gives the ranking more to match on."
              : "Ranking fell back to matching literal words only. Try a performer's name, or set a GEMINI_API_KEY to match on meaning."}
          </span>
        </>
      )}
    </div>
  );
}
