"""Casting Agent.

Describe the actor you want in your own words; get the most relevant
actor-looks back, each with the phrases that justify it and one thing it costs
you. It ranks and explains. It never picks.

Two layers, and the boundary between them is the point:

    domain/     records and the synthetic catalog. No AI, no network, and no
                knowledge of how anything is ranked.
    reasoning/  the scorer and the explainer. The only layer permitted to
                import a model, through the single seam in llm.py.

`tests/test_architecture.py` enforces that. A catalog that can see the scorer
is a catalog that can be shaped to flatter it, which is the circularity
objection arriving through the back door.
"""
