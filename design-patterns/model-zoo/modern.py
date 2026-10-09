#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Model zoo, MODERN shape: the same five creational patterns, absorbed by the language.

    Builder          -> keyword arguments with defaults; __post_init__ does build()'s validation
    Prototype        -> frozen presets; dataclasses.replace() copies with changes, and re-validates
    Abstract Factory -> one registered function returns the matched (model, preprocessor) Bundle
    Factory Method   -> @register("unet") adds a creator to a dict; nothing central is edited
    Singleton        -> @cache on get_settings(); callers may pass their own settings instead

Open next to classic.py: the scenario is the same and so is the transcript.

Run:  uv run modern.py
"""
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import cache


# ── Products: stand-ins. Real UNet and ViT would differ in behaviour, not name ─

@dataclass(frozen=True)
class Model:
    arch: str
    config: "ModelConfig"
    device: str

    def __str__(self) -> str:
        c = self.config
        return f"{self.arch:<4} depth={c.depth:<2} width={c.width:<3} dropout={c.dropout} on {self.device}"


@dataclass(frozen=True)
class Preprocessor:
    steps: tuple[str, ...]

    def __str__(self) -> str:
        return " → ".join(self.steps)


# ── Singleton -> a cached getter, and an argument you're free to override ────

@dataclass(frozen=True)
class Settings:
    device: str = "cpu"


@cache
def get_settings() -> Settings:
    return Settings()


# ── Builder -> keyword arguments; Prototype -> frozen values + replace() ──────

@dataclass(frozen=True)
class ModelConfig:
    arch: str
    depth: int = 4
    width: int = 64
    dropout: float = 0.0

    def __post_init__(self) -> None:            # runs on every construction, replace() included
        if self.depth < 1:
            raise ValueError("depth must be at least 1")
        if not 0 <= self.dropout < 1:
            raise ValueError("dropout must be in [0, 1)")


# Frozen, so sharing them is safe: nobody can change a preset by accident.
PRESETS = {
    "unet-small": ModelConfig("unet", depth=3, width=32),
    "vit-base": ModelConfig("vit", depth=12, width=768, dropout=0.1),
}


# ── Abstract Factory + Factory Method -> a registry of creator functions ─────

@dataclass(frozen=True)
class Bundle:
    """What one architecture needs, returned together so the parts always match."""
    model: Model
    preprocessor: Preprocessor


type Family = Callable[[ModelConfig, Settings], Bundle]
_REGISTRY: dict[str, Family] = {}


def register(arch: str) -> Callable[[Family], Family]:
    def add(family: Family) -> Family:
        _REGISTRY[arch] = family
        return family
    return add


@register("unet")
def unet(config: ModelConfig, settings: Settings) -> Bundle:
    return Bundle(Model("UNet", config, settings.device), Preprocessor(("resize 256", "z-score")))


@register("vit")
def vit(config: ModelConfig, settings: Settings) -> Bundle:
    return Bundle(Model("ViT", config, settings.device), Preprocessor(("resize 224", "patch 16")))


def create_model(config: ModelConfig, *, settings: Settings | None = None) -> Bundle:
    if config.arch not in _REGISTRY:
        raise ValueError(f"unknown arch {config.arch!r}; registered: {sorted(_REGISTRY)}")
    return _REGISTRY[config.arch](config, settings if settings is not None else get_settings())


# ── Composition root ─────────────────────────────────────────────────────────

def run() -> list[str]:
    out: list[str] = []

    def show(label: str, bundle: Bundle) -> None:
        out.append(f"{label:<11} {bundle.model}  ← {bundle.preprocessor}")

    settings = get_settings()
    out.append(f"settings    device={settings.device}, one shared object: {settings is get_settings()}")

    show("unet-small", create_model(PRESETS["unet-small"]))
    tuned = replace(PRESETS["unet-small"], dropout=0.2)    # Prototype: copy-with-changes in one step
    show("+ dropout", create_model(tuned))
    out.append(f"preset      unet-small still has dropout={PRESETS['unet-small'].dropout}")
    show("vit-base", create_model(PRESETS["vit-base"]))

    # Nothing global to change and restore: pass different settings for this one call.
    show("on cuda", create_model(PRESETS["unet-small"], settings=Settings(device="cuda")))
    out.append(f"settings    device={get_settings().device} afterwards")

    for bad in (lambda: ModelConfig("unet", dropout=1.5), lambda: create_model(ModelConfig("resnet"))):
        try:
            bad()
        except ValueError as error:
            out.append(f"rejected    {error}")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
