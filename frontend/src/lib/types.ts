// Mirrors backend/casting/serialize.py. If a shape changes there, it changes here.

export type Fluency = "native" | "fluent" | "conversational";
export type Kind = "human" | "ai";

export interface Look {
  id: string;
  setting: string;
  scene: string;
  wardrobe: string;
  framing: string[];
}

export interface Actor {
  id: string;
  name: string;
  kind: Kind;
  age_band: string;
  presents_as: string;
  languages: Record<string, Fluency>;
  language_text: string;
  appearance: string;
  delivery: string;
  voice: string[];
  look_count: number;
  settings: string[];
  portrait_seed: number;
  planted: string | null;
}

export interface MatchScore {
  score: number;
  evidence: string[];
  source: "model" | "lexical";
}

export interface Sentence {
  text: string;
  cites: string[];
}

export interface ResultItem {
  rank: number;
  actor: Actor;
  look: Look;
  match: MatchScore;
  rationale: { text: string; sentences: Sentence[]; cites: string[] };
  /** Present in the payload; deliberately not rendered. The brief rules out
   *  reservations and warning callouts, and the type stays here only so this
   *  file remains a faithful mirror of serialize.py. */
  reservation: { kind: string; text: string; cites: string[] };
}

export interface Results {
  query: { text: string; kind: Kind | null; limit: number };
  items: ResultItem[];
  /** Performers matched by name. Populated on the "name" and "both" routes. */
  actors: Actor[];
  matched_names: number;
  /** Which search the server ran. The browser reports it; it does not decide it. */
  route: "name" | "description" | "both" | "empty";
  seed: number;
  roster_size: number;
  look_count: number;
  /** "none" on a pure name lookup — no scorer ran, so none is named. */
  scorer: "model" | "lexical" | "none";
  model_used: boolean;
  returned: number;
}

export interface Meta {
  examples: { label: string; text: string }[];
  default_seed: number;
  /** The default seed's roster, so a search in flight can say what it is reading. */
  roster_size: number;
  look_count: number;
  model_available: boolean;
  catalog_notice: string;
  scorer_notice: string;
  kinds: Kind[];
  settings: string[];
}
