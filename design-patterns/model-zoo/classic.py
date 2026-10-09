#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Model zoo, CLASSIC shape: the five GoF creational patterns as the book draws them.

    Builder          : ConfigBuilder sets one field per call, and build() validates the result
    Prototype        : PRESETS holds ready-made configs; clone() copies one before you change it
    Abstract Factory : ModelFamily creates a model *and* the preprocessor that matches it
    Factory Method   : each family subclass overrides create_model() / create_preprocessor(),
                       and the base class's load() calls them without naming a concrete class
    Singleton        : Settings.instance() returns the one shared settings object

The Builder here is the fluent form (Effective Java) most codebases mean by "builder".
GoF's original Builder also has a Director; see the README's Variants section.

Open next to modern.py: the scenario is the same and so is the transcript.

Run:  uv run classic.py
"""
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass


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


# ── Singleton: one instance per process, reached through the class ───────────

class Settings:
    _instance: "Settings | None" = None

    def __init__(self) -> None:
        self.device = "cpu"

    @classmethod
    def instance(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# ── Prototype: an object that can copy itself ────────────────────────────────

class ModelConfig:
    def __init__(self, arch: str, depth: int, width: int, dropout: float) -> None:
        self.arch, self.depth, self.width, self.dropout = arch, depth, width, dropout

    def clone(self) -> "ModelConfig":
        """A copy you may change without touching the original."""
        return copy.copy(self)


# ── Builder: set fields step by step, validate once at the end ───────────────

class ConfigBuilder:
    def __init__(self, arch: str) -> None:
        self._arch, self._depth, self._width, self._dropout = arch, 4, 64, 0.0

    def depth(self, n: int) -> "ConfigBuilder":
        self._depth = n
        return self

    def width(self, n: int) -> "ConfigBuilder":
        self._width = n
        return self

    def dropout(self, p: float) -> "ConfigBuilder":
        self._dropout = p
        return self

    def build(self) -> ModelConfig:
        if self._depth < 1:
            raise ValueError("depth must be at least 1")
        if not 0 <= self._dropout < 1:
            raise ValueError("dropout must be in [0, 1)")
        return ModelConfig(self._arch, self._depth, self._width, self._dropout)


# The prototype registry: clone these, never change them.
PRESETS = {
    "unet-small": ConfigBuilder("unet").depth(3).width(32).build(),
    "vit-base": ConfigBuilder("vit").depth(12).width(768).dropout(0.1).build(),
}


# ── Abstract Factory, built from Factory Methods ─────────────────────────────

class ModelFamily(ABC):
    """Everything one architecture needs, made by one object so the parts always match."""

    @abstractmethod
    def create_model(self, config: ModelConfig) -> Model: ...

    @abstractmethod
    def create_preprocessor(self) -> Preprocessor: ...

    def load(self, config: ModelConfig) -> tuple[Model, Preprocessor]:
        """The creator's own operation: it uses the factory methods, never a concrete class."""
        return self.create_model(config), self.create_preprocessor()


class UNetFamily(ModelFamily):
    def create_model(self, config: ModelConfig) -> Model:
        return Model("UNet", config, Settings.instance().device)   # hidden global dependency

    def create_preprocessor(self) -> Preprocessor:
        return Preprocessor(("resize 256", "z-score"))


class ViTFamily(ModelFamily):
    def create_model(self, config: ModelConfig) -> Model:
        return Model("ViT", config, Settings.instance().device)

    def create_preprocessor(self) -> Preprocessor:
        return Preprocessor(("resize 224", "patch 16"))


def family_for(arch: str) -> ModelFamily:
    """Pick the concrete factory. Every new architecture means editing this function."""
    if arch == "unet":
        return UNetFamily()
    if arch == "vit":
        return ViTFamily()
    raise ValueError(f"unknown arch {arch!r}; registered: ['unet', 'vit']")


# ── Composition root ─────────────────────────────────────────────────────────

def run() -> list[str]:
    out: list[str] = []

    def show(label: str, model: Model, preprocessor: Preprocessor) -> None:
        out.append(f"{label:<11} {model}  ← {preprocessor}")

    settings = Settings.instance()
    out.append(f"settings    device={settings.device}, one shared object: {settings is Settings.instance()}")

    show("unet-small", *family_for("unet").load(PRESETS["unet-small"]))
    tuned = PRESETS["unet-small"].clone()       # Prototype: copy first, then change the copy
    tuned.dropout = 0.2
    show("+ dropout", *family_for(tuned.arch).load(tuned))
    out.append(f"preset      unet-small still has dropout={PRESETS['unet-small'].dropout}")
    show("vit-base", *family_for("vit").load(PRESETS["vit-base"]))

    Settings.instance().device = "cuda"         # the only way in is to change the global...
    try:
        show("on cuda", *family_for("unet").load(PRESETS["unet-small"]))
    finally:
        Settings.instance().device = "cpu"      # ...and to remember to put it back
    out.append(f"settings    device={Settings.instance().device} afterwards")

    for bad in (lambda: ConfigBuilder("unet").dropout(1.5).build(), lambda: family_for("resnet")):
        try:
            bad()
        except ValueError as error:
            out.append(f"rejected    {error}")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
