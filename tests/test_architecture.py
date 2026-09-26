"""Guards the layering described in NOTES.md, so it cannot silently erode."""

import ast
from collections.abc import Callable
from pathlib import Path

import pytest

import podcast_service

PACKAGE_ROOT = Path(podcast_service.__file__).parent
SRC_ROOT = PACKAGE_ROOT.parent

# Which top-level parts of `podcast_service` each layer may import (besides itself).
ALLOWED_DEPENDENCIES = {
    "domain": set(),
    "application": {"domain"},
    "infrastructure": {"domain", "application"},
}


def _modules() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _dotted(path: Path) -> str:
    parts = path.relative_to(SRC_ROOT).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(path: Path) -> list[ast.ImportFrom]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("podcast_service.")
    ]


def _exports() -> dict[str, set[str]]:
    exports: dict[str, set[str]] = {}
    for init in PACKAGE_ROOT.rglob("__init__.py"):
        for node in ast.parse(init.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ):
                exports[_dotted(init)] = set(ast.literal_eval(node.value))
    return exports


def _layer_violations() -> list[str]:
    violations = []
    for path in _modules():
        layer = _dotted(path).split(".")[1] if "." in _dotted(path) else None
        if layer not in ALLOWED_DEPENDENCIES:
            continue  # api, container and config sit at the edge and may import anything
        for node in _imports(path):
            target = node.module.split(".")[1]  # type: ignore[union-attr]
            if target != layer and target not in ALLOWED_DEPENDENCIES[layer]:
                violations.append(f"{_dotted(path)} imports {node.module}")
    return violations


def _deep_import_violations() -> list[str]:
    exports = _exports()
    violations = []
    for path in _modules():
        own_package = _dotted(path) if path.name == "__init__.py" else _dotted(path.parent)
        for node in _imports(path):
            package = node.module.rsplit(".", 1)[0]  # type: ignore[union-attr]
            if node.module in exports or package == own_package or package not in exports:
                continue
            exported = {alias.name for alias in node.names} & exports[package]
            if exported:
                violations.append(
                    f"{_dotted(path)} imports {sorted(exported)} from {node.module}; "
                    f"use `from {package} import ...`"
                )
    return violations


@pytest.mark.parametrize(
    "check",
    [_layer_violations, _deep_import_violations],
    ids=["dependencies-point-inwards", "packages-are-imported-through-their-api"],
)
def test_architecture(check: Callable[[], list[str]]) -> None:
    assert check() == []
