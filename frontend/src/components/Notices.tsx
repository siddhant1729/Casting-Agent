import type { Results } from "../lib/types";

// Which path produced what you are looking at. A ranking from the model and a
// ranking from the offline word-overlap fallback are different artefacts, and
// the API reports which ran — so the screen says so rather than letting a
// degraded result pass as a good one.

export function Notices({ results, scorerNote }: { results: Results; scorerNote: string }) {
  const offline = !results.model_used;
  return (
    <>
      <div className="notices">
        <span className="notice">
          <b>catalog</b> synthetic · seed {results.seed}
        </span>
        <span className={`notice${offline ? " warn" : ""}`}>
          <b>ranking</b>{" "}
          {offline ? "literal words · offline fallback" : "on meaning · model"}
        </span>
        <span className="notice">
          <b>roster</b> {results.look_count} looks · {results.roster_size} actors
        </span>
        <span className="notice">
          <b>portraits</b> placeholder art
        </span>
      </div>
      {offline && <p className="muted" style={{ marginTop: 10 }}>{scorerNote}</p>}
    </>
  );
}
