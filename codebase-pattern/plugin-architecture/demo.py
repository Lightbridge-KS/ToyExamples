# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Six scenes through a manifest-first plugin host, with the [activate] trace on.

uv run demo.py
"""

import sys
from pathlib import Path

from host import MODULE_PREFIX, ActivationError, Registry, discover

HERE = Path(__file__).parent
PLUGINS = HERE / "plugins"
BROKEN = HERE / "plugins-broken"


def main() -> None:
    scene("1 · The palette, with no plugin code imported")
    # Discovery reads three plugin.toml files. The host now knows every command
    # and template, their titles, and their owners, and has imported nothing.
    reg = discover(PLUGINS)
    show_palette(reg)
    show_imported()

    scene("2 · Lazy activation: code is imported on first use, once")
    # The first run resolves "measure:to_cm": only now does measure.py load.
    # The second run reuses it. report_tools.py is still untouched.
    run(reg, "measure.to-cm", "A 12 mm nodule, previously 8 mm.")
    run(reg, "measure.to-cm", "Calcified granuloma, 4 mm.")
    show_imported()

    scene("3 · A data-only plugin: no code at all")
    # ct-brain-template has no Python file. The host renders its body itself.
    print(indent(reg.render("ct-brain")))
    show_imported()

    scene("4 · The gate runs before code: api version and schema")
    # Add the broken plugins. Each manifest is checked alone first.
    # too_new.py raises on import; we are still running, so it was never read.
    reg = discover(PLUGINS, BROKEN)
    show_rejected(reg, "too-new", "mri-knee-template")

    scene("5 · Conflicts are found from data, before any code runs")
    # measure and measure-fork both claim "measure.to-cm". The policy rejects
    # both: a healthy plugin goes down with the bad one, but no winner is picked
    # by folder order. measure_fork.py raises on import; it was never read.
    show_rejected(reg, "measure", "measure-fork")
    run(reg, "measure.to-cm", "A 12 mm nodule.")

    scene("6 · Manifest drift: found on first use, or earlier by check()")
    # impression-tools 0.2.0 renamed uppercase() to shout(); its manifest still
    # says uppercase. The data cannot know. The failure is per command.
    report = reg.render("ct-brain")
    run(reg, "impression.extract", report)
    run(reg, "impression.uppercase", report)
    # check() is the contract test: it resolves every handler, so it imports
    # every code plugin. That is fine in CI, and wrong at startup.
    print("\n>>> reg.check()")
    for problem in reg.check():
        print(f"  ✗ {problem}")


# ── helpers ──


def scene(title: str) -> None:
    print(f"\n━━ {title} " + "━" * max(0, 72 - len(title)))


def run(reg: Registry, command_id: str, text: str) -> None:
    first = text.strip().splitlines()[0]
    preview = first if first == text.strip() else f"{first} …"
    print(f"\n>>> run({command_id!r}, {preview!r})")
    try:
        print(f"  → {reg.run(command_id, text)}")
    except (ActivationError, LookupError) as e:
        print(f"  ✗ {type(e).__name__}: {e}")


def show_palette(reg: Registry) -> None:
    print(f"\n  {'point':<10} {'id':<20} {'title':<24} plugin")
    for point, c, owner in reg.palette():
        print(f"  {point:<10} {c.id:<20} {c.title:<24} {owner}")


def show_rejected(reg: Registry, *folders: str) -> None:
    for folder in folders:
        print(f"  rejected {folder:<18} {reg.rejected[folder]}")


def show_imported() -> None:
    imported = sorted(m for m in sys.modules if m.startswith(MODULE_PREFIX))
    print(f"\n  plugin modules in sys.modules: {imported}")


def indent(text: str) -> str:
    return "\n".join(f"  │ {line}" for line in text.strip().splitlines())


if __name__ == "__main__":
    main()
