import type { Meta, Results } from "./types";

// Render's blueprint fills VITE_API from the API service's `host` property,
// which is a bare hostname — no scheme. Adding https:// here keeps the
// deployment config declarative instead of asking someone to paste the full
// URL by hand, and an explicit http:// or https:// is left untouched.
const RAW_BASE = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";
const BASE = (/^https?:\/\//.test(RAW_BASE) ? RAW_BASE : `https://${RAW_BASE}`)
  .replace(/\/$/, "");

export async function fetchMeta(): Promise<Meta> {
  const response = await fetch(`${BASE}/api/meta`);
  if (!response.ok) throw new Error("meta failed");
  return response.json();
}

// One box, both searches. The server routes a typed query to the name lookup,
// to the ranking, or to both, and reports which in `route`. The browser never
// chooses the path, and never re-scores or re-sorts: a second ordering
// implemented in TypeScript is a second thing to keep true.
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

// `fetch` rejects with a bare TypeError when the request never reached the
// server at all — the API asleep, down, or unreachable. "TypeError: Failed to
// fetch" is the browser's words for that, and it tells the person reading it
// nothing they can act on. Everything else is an HTTP status the API did send.
//
// Not `instanceof TypeError`: that is false across realms (an iframe, a test
// harness), and each engine words the same failure differently — Chrome "Failed
// to fetch", Firefox "NetworkError when attempting to fetch resource", Safari
// "Load failed". Matching the name and those wordings covers all three, and the
// worst case of a miss is the fallback message below rather than a wrong claim.
const NETWORK_FAILURE = /failed to fetch|networkerror|network request failed|load failed/i;

export function describeFailure(error: unknown): string {
  const detail = error instanceof Error ? error.message : String(error);
  const name = error instanceof Error ? error.name : "";
  if (name === "TypeError" || NETWORK_FAILURE.test(detail)) {
    return "Can't reach the API. It may be asleep — free instances shut down " +
      "after a while and take up to a minute to start.";
  }
  return `The search didn't finish (${detail}).`;
}
