import { useCallback, useEffect, useRef, useState } from "react";
import { LookCard } from "../components/LookCard";
import { Portrait } from "../components/Portrait";
import { search, searchActors } from "../lib/api";
import type { ActorSearchResults, Meta, Results } from "../lib/types";

// One query, two searches, same catalog and seed.
//
// The left panel is the roster's existing name search, hitting POST /api/actors.
// Its empty result for the default query is computed, not staged — nobody is
// *named* "warm, credible, explains money without sounding like a bank". That
// is the entire argument, so faking it would be self-defeating.

const DEFAULT_QUERY = "warm, credible, explains money without sounding like a bank";

export function Compare({ meta }: { meta: Meta }) {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [names, setNames] = useState<ActorSearchResults | null>(null);
  const [ranked, setRanked] = useState<Results | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef(0);

  const run = useCallback(async (text: string) => {
    const ticket = ++pending.current;
    setBusy(true);
    setError(null);
    try {
      // Both panels are asked at once. Neither is derived from the other.
      const [left, right] = await Promise.all([
        searchActors(text, null, meta.default_seed),
        search(text, null, meta.default_seed),
      ]);
      if (ticket === pending.current) {
        setNames(left);
        setRanked(right);
      }
    } catch (e) {
      if (ticket === pending.current) setError(String(e));
    } finally {
      if (ticket === pending.current) setBusy(false);
    }
  }, [meta.default_seed]);

  useEffect(() => { run(DEFAULT_QUERY); }, [run]);

  return (
    <>
      <section className="region">
        <div className="region-head">
          <span className="region-title">Live comparison · keyword vs semantic</span>
          <span className="region-note">
            One query. The roster's name search on the left, this agent on the right.
          </span>
        </div>

        <label className="sr-only" htmlFor="compare-query">Query for both panels</label>
        <textarea
          id="compare-query"
          className="brief"
          style={{ minHeight: 72 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(query);
          }}
        />
        <div style={{ marginTop: 14, display: "flex", gap: 12, alignItems: "center" }}>
          <button className="btn" disabled={busy} onClick={() => run(query)}>
            {busy ? "Running both…" : "Run both searches"}
          </button>
          <button className="btn ghost" onClick={() => { setQuery(DEFAULT_QUERY); run(DEFAULT_QUERY); }}>
            Reset query
          </button>
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="compare">
        <section className="region" aria-labelledby="panel-search">
          <div className="compare-head">
            <h2 id="panel-search">Search actors</h2>
            <span className="how">matches on name only</span>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {names ? `${names.matched} of ${names.roster_size} actors` : "…"}
          </p>

          {names && names.actors.length === 0 ? (
            <div className="empty-state">
              <strong>No actors found</strong>
              A name search compares your words against performers' names. Nobody on the
              roster is called “{names.query.text}”.
              <span className="why">
                searched field: {names.search_field} · {names.roster_size} actors ·
                seed {names.seed}
              </span>
            </div>
          ) : (
            <div className="grid-actors">
              {names?.actors.map((actor) => (
                <div className="grid-actor" key={actor.id}>
                  <Portrait seed={actor.portrait_seed} size={96} />
                  <div className="name">{actor.name}</div>
                  <div className="meta">{actor.look_count} looks · {actor.kind}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="region" aria-labelledby="panel-casting">
          <div className="compare-head">
            <h2 id="panel-casting">Casting</h2>
            <span className="how">
              matches on meaning · {ranked?.model_used ? "model" : "offline fallback"}
            </span>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {ranked ? `${ranked.returned} of ${ranked.look_count} looks ranked` : "…"}
          </p>

          {ranked && ranked.items.length === 0 ? (
            <div className="empty-state">
              <strong>0 looks match</strong>
              All {ranked.look_count} looks were scored and none scored above zero.
              <span className="why">
                {ranked.model_used
                  ? "Model path. Broaden the description."
                  : "Offline word-overlap fallback — set GEMINI_API_KEY for semantic matching."}
              </span>
            </div>
          ) : (
            <div className="looks">
              {ranked?.items.slice(0, 6).map((item) => (
                <LookCard key={`${item.actor.id}-${item.look.id}`} item={item} />
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
