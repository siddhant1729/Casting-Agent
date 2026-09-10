"""The layer a model is allowed into, and the only one.

`llm.py` is the single seam. Everything here still works without it: the
scorer falls back to word overlap and the explainer never used a model at all.
The fallback is deliberately weak rather than propped up with a hand-written
synonym table — the catalog and the query vocabulary are disjoint by
construction, so word overlap genuinely cannot bridge them, and a padded
fallback would hide exactly the gap this product exists to close.
"""
