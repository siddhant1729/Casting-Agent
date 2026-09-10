import type { ActorSearchResults, Meta, Results } from "./types";

const BASE = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";

export async function fetchMeta(): Promise<Meta> {
  const response = await fetch(`${BASE}/api/meta`);
  if (!response.ok) throw new Error("meta failed");
  return response.json();
}

// Ranking happens on the server. The browser never re-scores or re-sorts: a
// second ordering implemented in TypeScript is a second thing to keep true.
export async function search(
  query: string,
  kind: string | null,
  seed: number,
): Promise<Results> {
  const response = await fetch(`${BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, kind, seed }),
  });
  if (!response.ok) throw new Error(`search failed: ${response.status}`);
  return response.json();
}

// The roster's existing name search, over the same catalog and seed. Used by
// the comparison view's left panel so its empty result is computed rather than
// staged — no performer is *named* "warm, credible, explains money...".
export async function searchActors(
  query: string,
  kind: string | null,
  seed: number,
  limit = 24,
): Promise<ActorSearchResults> {
  const response = await fetch(`${BASE}/api/actors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, kind, seed, limit }),
  });
  if (!response.ok) throw new Error(`actors failed: ${response.status}`);
  return response.json();
}
