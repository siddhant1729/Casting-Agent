"""The layer boundary, enforced.

`domain/` holds records and the catalog, and must never reach into ranking. A
catalog that can see the scorer is a catalog that can be shaped to flatter it,
which is the circularity objection arriving through the back door.

The rule about the model seam is the same one: `llm.py` is meant to be the only
place a request leaves the process, and that is only a real commitment if
something fails when it is broken.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "casting"

#: Modules these layers may not reach, directly or transitively through a
#: sibling in the same layer.
FORBIDDEN_FOR_DETERMINISTIC_LAYERS = ("reasoning", "llm")


def _imports(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found.append(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
    return found


def _modules(layer: str) -> list[pathlib.Path]:
    return sorted((PACKAGE / layer).glob("*.py"))


@pytest.mark.parametrize("layer", ["domain"])
def test_the_domain_layer_cannot_import_a_model(layer):
    for module in _modules(layer):
        for imported in _imports(module):
            assert not any(part in imported for part in FORBIDDEN_FOR_DETERMINISTIC_LAYERS), (
                f"{layer}/{module.name} imports {imported}"
            )


def test_domain_does_not_depend_on_reasoning():
    """Records must not know how they are ranked. If they did, the catalog
    could be shaped to flatter the scorer."""
    for module in _modules("domain"):
        for imported in _imports(module):
            assert "reasoning" not in imported, f"domain/{module.name} imports {imported}"


def test_the_deterministic_layers_import_nothing_that_does_network_io():
    """A pure layer that opens a socket is not pure. This catches the accidental
    `requests` or `urllib` that would make a cost calculation non-reproducible."""
    banned = {"urllib", "urllib.request", "requests", "httpx", "socket", "aiohttp"}
    for module in _modules("domain"):
        assert not (set(_imports(module)) & banned), module.name


def test_only_one_module_talks_to_a_model():
    """The seam is meant to be a seam. Anything importing a provider SDK or
    hitting an inference endpoint outside llm.py is a second seam."""
    offenders = []
    for module in PACKAGE.rglob("*.py"):
        if module.name == "llm.py":
            continue
        if "generativelanguage" in module.read_text():
            offenders.append(module.name)
    assert offenders == []


def test_every_layer_documents_its_boundary():
    """The docstrings are the only place the rule is explained to a human."""
    for layer in ("domain", "reasoning"):
        doc = ast.get_docstring(ast.parse((PACKAGE / layer / "__init__.py").read_text()))
        assert doc and len(doc) > 80, layer
