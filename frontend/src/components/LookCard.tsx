import { Portrait } from "./Portrait";
import type { ResultItem } from "../lib/types";

// One actor-LOOK. Never one actor.
//
// The same performer appears more than once here with different looks at
// different ranks, and deduplicating by actor would collapse exactly the thing
// the feature exists to show — a kitchen look and a beach look are different
// casting decisions with the same face.
//
// Nothing on this card is selectable. The tool ranks and explains; the pick is
// the user's.

// The API's rationale is three sentences: what matched, the look, then the
// performer's demographics and language. The first two are rendered here — the
// third is already on screen as tags, and repeating it reads as padding.
//
// Every sentence is generated server-side by slot-fill over cited record
// fields, so nothing here is reworded or inferred. Rewriting them client-side
// would break that guarantee silently.
const RATIONALE_SENTENCES = 2;

export function LookCard({ item }: { item: ResultItem }) {
  const { actor, look, match, rationale } = item;
  const text = rationale.sentences
    .slice(0, RATIONALE_SENTENCES)
    .map((sentence) => sentence.text)
    .join(" ");

  return (
    <article className="look">
      <div className="look-portrait">
        <Portrait seed={actor.portrait_seed} />
        <span className="setting-tag">{look.setting}</span>
      </div>

      <div>
        <div className="look-head">
          <span className="rank" aria-hidden="true">{item.rank}</span>
          <h3>
            {actor.name}
            <span className="sr-only"> — rank {item.rank}</span>
          </h3>

          {/* The look's own label, taken from the record: its setting and the
              scene as written in the catalog. Not a coined creative title —
              that would be a claim the payload does not make. */}
          <span className="look-label">
            Look: {look.setting} · {look.scene}
          </span>

          <span className="match">
            <span className="dot" aria-hidden="true" />
            {Math.round(match.score * 100)}% Match
          </span>
        </div>

        <p className="rationale">{text}</p>

        <div className="tags">
          <span className="tag">
            <b>Languages:</b> {actor.language_text}
          </span>
          <span className="tag">
            <b>Setting:</b> {look.setting}, {look.wardrobe}
          </span>
        </div>
      </div>
    </article>
  );
}
