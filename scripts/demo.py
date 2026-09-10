"""Run the seeded example searches in a terminal.

    .venv/bin/python scripts/demo.py [seed]

Set GEMINI_API_KEY first to see what the product actually does. Without it this
prints the word-overlap fallback, which is worth looking at once: the catalog
shares no vocabulary with the queries, so the fallback ranks on literal words
and visibly misses people it should find.
"""

from __future__ import annotations

import sys

from casting.pipeline import EXAMPLE_QUERIES, from_text
from casting.reasoning.llm import get_client

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7


def main() -> None:
    client = get_client()
    configured = "Gemini" if client.available else "word overlap (no GEMINI_API_KEY)"
    print(f"Synthetic catalog, seed {SEED}. Configured scorer: {configured}\n")

    for example in EXAMPLE_QUERIES:
        results = from_text(example["text"], seed=SEED, limit=5, client=client)
        print("=" * 78)
        # Report what actually ran, not what was configured. A key that is
        # present but rate-limited degrades silently, and a header claiming
        # "Gemini" over word-overlap results is the most misleading thing this
        # script could print.
        if results.scorer != "model":
            print(f"!! fell back to word overlap — {client.last_error or 'no model result'}")
        print(f"{example['label']}: {example['text']}")
        print("=" * 78)
        if not results.items:
            print("  nothing matched\n")
            continue
        for item in results.items:
            match = item.match
            print(f"{item.rank}. {match.actor.name:<13} {match.score:>5.0%}  "
                  f"{match.look.setting.value:<10} {match.actor.kind.value}")
            print(f"   {item.rationale.text}")
            print(f"   reservation: {item.reservation.text}")
            print()


if __name__ == "__main__":
    main()
