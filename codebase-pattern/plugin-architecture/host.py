"""
Plug-in architecture, manifest-first: the host of a tiny radiology report workbench.

A plugin is a folder: a plugin.toml (data) and, optionally, Python modules (code).
The host learns everything a plugin adds from the data, and imports the code only
when a contribution is first used.

    DISCOVER : read every plugin.toml → validate → admit or reject     (no plugin code runs)
    REGISTRY : one table per extension point, built from data alone
    ACTIVATE : resolve "module:function" on first use, once            (now plugin code runs)
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from types import ModuleType
from typing import cast

API_VERSION = (
    1  # the host contract's major version; a manifest names the one it was built for
)
MODULE_PREFIX = (
    "plugins."  # activated plugin modules sit in sys.modules under this prefix
)


# ═════════════════════ EXTENSION POINTS (owned by the host) ═════════════════════
# The host decides WHAT can be contributed; a plugin only fills these slots.
# Each point is a schema: its dataclass fields are the manifest keys it requires.


@dataclass(frozen=True)
class Command:
    """Code-backed. The host knows id and title now; it imports `handler` on first run."""

    id: str
    title: str
    handler: (
        str  # "module:function" in the plugin folder, with the signature (str) -> str
    )


@dataclass(frozen=True)
class Template:
    """Pure data. The host renders the body itself, so no plugin code exists or runs."""

    id: str
    title: str
    body: str


Contribution = Command | Template
EXTENSION_POINTS: dict[str, type[Contribution]] = {
    "commands": Command,
    "templates": Template,
}


# ══════════════════════════════════ THE GATE ══════════════════════════════════


class ManifestError(Exception):
    """A manifest failed the gate. Its plugin is rejected; its code is never read."""


class ActivationError(Exception):
    """A declared handler did not resolve: the manifest and the code disagree."""


@dataclass(frozen=True)
class Manifest:
    id: str
    version: str
    api: int
    folder: Path
    contributes: dict[str, list[Contribution]]


def parse_manifest(folder: Path) -> Manifest:
    """Validate one plugin.toml. Data in, typed data out, or ManifestError."""
    raw = tomllib.loads((folder / "plugin.toml").read_text())
    for key, kind in (("id", str), ("version", str), ("api", int)):
        if not isinstance(raw.get(key), kind):
            raise ManifestError(f"{key}: required, must be {kind.__name__}")
    if raw["api"] != API_VERSION:
        raise ManifestError(
            f"api: built for host api {raw['api']}, this host is {API_VERSION}"
        )

    contributes: dict[str, list[Contribution]] = {}
    for point, items in raw.get("contributes", {}).items():
        if point not in EXTENSION_POINTS:
            raise ManifestError(f"contributes.{point}: no such extension point")
        if not isinstance(items, list):
            raise ManifestError(
                f"contributes.{point}: must be an array of tables, [[...]]"
            )
        schema = EXTENSION_POINTS[point]
        keys = {f.name for f in fields(schema)}
        contributes[point] = []
        for i, item in enumerate(items):
            where = f"contributes.{point}[{i}]"
            if missing := sorted(keys - item.keys()):
                raise ManifestError(f"{where}.{missing[0]}: required")
            if unknown := sorted(item.keys() - keys):
                raise ManifestError(f"{where}.{unknown[0]}: unknown key")
            if wrong := sorted(k for k in keys if not isinstance(item[k], str)):
                raise ManifestError(f"{where}.{wrong[0]}: must be str")
            contributes[point].append(schema(**item))
    return Manifest(raw["id"], raw["version"], raw["api"], folder, contributes)


def discover(*roots: Path) -> Registry:
    """Startup: read every <root>/*/plugin.toml, then admit or reject. Imports nothing."""
    admitted: list[Manifest] = []
    rejected: dict[str, str] = {}  # plugin folder name → reason
    for folder in sorted(
        p.parent for root in roots for p in root.glob("*/plugin.toml")
    ):
        try:
            admitted.append(parse_manifest(folder))
        except ManifestError as e:
            rejected[folder.name] = str(e)

    # Whole-system check, still data only: every contribution id has exactly one owner.
    claims: dict[tuple[str, str], list[Manifest]] = {}
    for m in admitted:
        for point, items in m.contributes.items():
            for c in items:
                claims.setdefault((point, c.id), []).append(m)
    for (point, cid), owners in claims.items():
        # Policy: reject every claimant, so no winner is picked by folder order.
        if len(owners) > 1:
            for m in owners:
                others = ", ".join(o.id for o in owners if o is not m)
                kind = point.removesuffix("s")
                rejected[m.folder.name] = f"{kind} {cid!r} is also claimed by {others}"

    return Registry([m for m in admitted if m.folder.name not in rejected], rejected)


# ═════════════════════════════════ THE REGISTRY ═════════════════════════════════


class Registry:
    """What the host knows: built from manifests, holding plugin code only once activated."""

    def __init__(self, manifests: list[Manifest], rejected: dict[str, str]):
        self.rejected = rejected
        self._index: dict[tuple[str, str], tuple[Contribution, Manifest]] = {
            (point, c.id): (c, m)
            for m in manifests
            for point, items in m.contributes.items()
            for c in items
        }

    def palette(self) -> list[tuple[str, Contribution, str]]:
        """Every contribution, with the id of the plugin that owns it. Data only."""
        return [(point, c, m.id) for (point, _), (c, m) in sorted(self._index.items())]

    def render(self, template_id: str) -> str:
        template, _ = self._lookup("templates", template_id)
        assert isinstance(template, Template)
        return template.body

    def run(self, command_id: str, text: str) -> str:
        command, owner = self._lookup("commands", command_id)
        assert isinstance(command, Command)
        return self._resolve(command, owner)(text)

    def check(self) -> list[str]:
        """Contract test: resolve every declared handler and report the ones that drifted.

        It imports every code plugin, so run it in CI, never at startup.
        """
        problems = []
        for c, owner in sorted(self._index.values(), key=lambda entry: entry[0].id):
            if not isinstance(c, Command):
                continue  # templates are data: nothing to resolve
            try:
                self._resolve(c, owner)
            except ActivationError as e:
                problems.append(f"{c.id}: {e}")
        return problems

    # ── internal ──

    def _lookup(self, point: str, cid: str) -> tuple[Contribution, Manifest]:
        if (point, cid) not in self._index:
            raise LookupError(f"no {point.removesuffix('s')} {cid!r}")
        return self._index[point, cid]

    def _resolve(self, command: Command, owner: Manifest) -> Callable[[str], str]:
        module_name, _, func_name = command.handler.partition(":")
        func = getattr(self._activate(owner, module_name), func_name, None)
        if not callable(func):
            raise ActivationError(
                f"{owner.id}: manifest names {command.handler!r}, "
                f"but {module_name}.py has no {func_name}()"
            )
        # A string crosses the seam, so no type checker sees the signature: (str) -> str
        # is a promise in the manifest's docs, not a fact the host can verify.
        return cast(Callable[[str], str], func)

    def _activate(self, owner: Manifest, module_name: str) -> ModuleType:
        """Import one plugin module on first use. sys.modules is the cache, so it runs once."""
        key = f"{MODULE_PREFIX}{owner.id}.{module_name}"
        if key in sys.modules:
            return sys.modules[key]
        path = owner.folder / f"{module_name}.py"
        if not path.is_file():
            raise ActivationError(
                f"{owner.id}: manifest names {module_name}.py, which is missing"
            )
        print(f"  [activate] {owner.id} ← {owner.folder.name}/{path.name}")
        spec = importlib.util.spec_from_file_location(key, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(
                module
            )  # the plugin's top-level code runs here, in-process
        except Exception as e:
            del sys.modules[key]
            raise ActivationError(
                f"{owner.id}: importing {path.name} raised {e!r}"
            ) from e
        return module
