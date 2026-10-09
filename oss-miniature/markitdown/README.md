# MarkItDown in miniature (toy example)

*Any file in, Markdown out, through one priority-ordered converter registry. This is the skeleton of
[microsoft/markitdown](https://github.com/microsoft/markitdown) in ~620 lines of stdlib Python
(docstrings included), with every file-format library stubbed out: a five-module library, a
one-module plugin, and a demo.*

```sh
# from this folder
uv run --exact demo.py                  # 7 scenes, with the dispatch trace on
uv run --exact --extra yaml demo.py     # as if `pip install minimd[yaml]`: scene 5 changes
uv run --with jupyterlab jupyter lab minimd.ipynb   # interactive walkthrough, stage by stage
```

Keep `--exact` on both. Without it, `uv run` leaves `pyyaml` installed after an `--extra` run.

```
markitdown/                       ← this example
├── pyproject.toml                the [yaml] extra, and the plugin's entry point
├── demo.py                       7 scenes; indents the trace by recursion depth
├── minimd.ipynb                  each stage on its own: contract, hints, guesses, registry, dispatch, plugins
├── samples/                      report.csv · supplies.csv (;-delimited) · config.yaml · settings.ini
└── src/
    ├── minimd/                   ← the library ("markitdown")
    │   ├── __init__.py           public API
    │   ├── _stream_info.py       StreamInfo
    │   ├── _base_converter.py    DocumentConverter, DocumentConverterResult
    │   ├── _exceptions.py        Unsupported vs FileConversion, MissingDependency
    │   ├── _markitdown.py        MarkItDown: registry, front doors, guessing, dispatch
    │   └── converters.py         PlainText · Csv · Yaml (optional dep) · Zip (recursive)
    └── minimd_sample_plugin/     ← a "third-party" plugin: Ini (new format) · SniffingCsv (shadow)
```

File and class names match markitdown's, so each toy piece maps onto a real one:

| Toy | markitdown (pinned at `a51f725`) | Kept / cut |
|---|---|---|
| `_stream_info.py` | [`_stream_info.py`][r-stream] | same |
| `_base_converter.py` | [`_base_converter.py`][r-base] | same contract; `text_content` alias cut |
| `_exceptions.py` | [`_exceptions.py`][r-exc] | same hierarchy |
| `_markitdown.py` | [`_markitdown.py`][r-convert] (783 lines) | `file:`/`http:` doors, global LLM options, deprecated args cut; plugin list cached with `@cache`, not a module global |
| `_sniff()` | [magika][r-guesses], an ML file-type model | magic bytes + "does it decode?" |
| `converters.py` | `converters/`, about 20 files | 4 converters, format libraries swapped for stdlib |
| `minimd_sample_plugin/` | [`markitdown-sample-plugin`][r-sample] + [`markitdown-ocr`][r-ocr] | new format + shadowing, one module |

## The idea

MarkItDown knows no file format. It is a **dispatcher**: a list of converters, each with a
priority, and a loop that asks them in order "is this yours?", then "convert it". The first
success wins. What a format needs lives in its converter. What *every* format needs (input
handling, type detection, ordering, error policy, output cleanup) lives once, in the dispatcher.

```
  path ────► convert_local ──┐
  stream ──► convert_stream ─┤  every door yields the same pair:
  "data:…" ► convert_uri ────┘  (seekable stream, base StreamInfo)
                               │
                               ▼
               _guesses():  hints  vs  _sniff(bytes)
                            agree → [merged]     conflict → [hints, sniffed]
                            … plus one final empty guess
                               │
                               ▼
  _convert():  for guess in guesses:
                 for converter in registry, sorted by priority:
                   accepts(stream, guess)? ── no ──────────────────────► next
                      │ yes
                   convert(stream, guess) ─── raises ─► record, rewind ─► next
                      │ returns
                   normalize ─► DocumentConverterResult        (first success wins)

               nobody accepted ────────────────► UnsupportedFormatException
               accepted, and every one raised ─► FileConversionException(attempts)

  registry, as dispatch sees it (plugins enabled):
    -1.0  SniffingCsvConverter    plugin: shadows the built-in CSV
     0.0  IniConverter            plugin: new format            ┐ specific formats;
     0.0  YamlConverter           needs minimd[yaml]            │ among equals, the
     0.0  CsvConverter                                          ┘ newest goes first
    10.0  ZipConverter ── each member ──► back into convert_stream()   ┐ generic
    10.0  PlainTextConverter                                           ┘ catch-alls
```

## Ten ideas, and where each lives

| # | Idea | Toy | markitdown |
|---|---|---|---|
| 1 | **The contract is two methods, one signature.** `accepts()` is a cheap yes/no from hints; `convert()` does the work. Same arguments, so a yes hands straight over. | `DocumentConverter` | [base][r-base] |
| 2 | **Hints are an immutable value.** `StreamInfo` is frozen; `copy_and_update()` merges (non-None wins), so one guess can fan out into several. | `StreamInfo` | [stream info][r-stream] |
| 3 | **Many doors, one room.** Path, stream, and URI (and, in markitdown, HTTP responses) each reduce to a seekable stream plus a base `StreamInfo`, then share one dispatch. | `convert*()` | [doors][r-doors] |
| 4 | **Don't trust the name.** Hints are cross-checked against the bytes. If they agree, one merged guess. If they conflict, both, hints first. Then an empty guess as a last resort. | `_guesses()`, `_sniff()` | [guesses][r-guesses] |
| 5 | **Order is data.** Lower priority first; ties go to the newest registration (`insert(0)` plus a stable sort). Specific formats sit at 0, catch-alls at 10, shadows below 0. | `register_converter()` | [register][r-register], [built-ins][r-builtins] |
| 6 | **First success wins; a failure is a record, not an exit.** A raising converter is recorded, the stream rewound, the next one asked. Only at the end do the records pick the error. | `_convert()` | [dispatch][r-convert] |
| 7 | **The stream position is shared state, guarded.** `accepts()` must rewind if it peeks; dispatch asserts that, and rewinds after every `convert()`. | the `assert` + `finally: seek` | [invariant][r-invariant] |
| 8 | **Optional dependencies fail soft.** A failed import is stored, not raised; `convert()` raises `MissingDependencyException` naming the extra. Installing the extra lights the converter up, with no core change. | `YamlConverter` | [guard][r-docx-guard], [raise][r-docx-raise] |
| 9 | **Recursion through your own registry.** `ZipConverter` holds the `MarkItDown` that owns it and sends each member back through dispatch, so an archive can hold anything any converter reads, plugins included. | `ZipConverter` | [zip][r-zip] |
| 10 | **A plugin is an entry point plus one function.** Found in installed-package metadata, loaded lazily, fault-isolated, off by default. It registers through the same public `register_converter()` the built-ins use. | `_load_plugins()`, `enable_plugins()` | [load][r-load], [enable][r-enable], [entry point][r-sample-ep] |
| + | **Cross-cutting policy lives once.** Trailing spaces and runs of blank lines are cleaned in the dispatcher, for every converter. | `_normalize()` | [normalize][r-normalize] |

## Seven scenes the demo shows

1. **Specific beats generic.** `report.csv`: CsvConverter (0.0) answers before PlainTextConverter (10.0), which would also accept it, is ever asked.
2. **Three doors, one dispatch.** The same CSV as a stream with a hint and as a `data:` URI. The guess line is identical in all three, and so is the output.
3. **No name? Ask the bytes.** Bare zip bytes, no hints: the sniffer supplies the only guess. Each member dispatches again (indented); `scan.bin` is skipped as unsupported.
4. **The name lies.** Zip bytes labelled `notes.txt`. Guess 1 (the hint): PlainText ✗ `UnicodeDecodeError`. Guess 2 (the bytes): Zip ✓. The recorded failure is dropped, because something succeeded.
5. **A missing library is a soft failure.** `config.yaml`: YamlConverter ✗ `MissingDependencyException`, then PlainText returns the raw YAML. With `--extra yaml`, the same call returns a bullet list.
6. **Two ways to fail.** A truncated zip → `FileConversionException` (someone tried, and failed). Unknown binary → `UnsupportedFormatException` (nobody tried).
7. **Plugins: opt-in, discovered, prioritized.** `supplies.csv` uses `;` and decimal commas, so the built-in splits `12,50` into two cells. The plugin's SniffingCsvConverter at -1.0 gets there first and fixes it. `settings.ini` is plain text without the plugin and a table per section with it.

## Why it works

- **Adding a format touches nothing else.** One class, one `register_converter()` call. The dispatcher, the other converters, and every caller stay as they are.
- **Detection is shared; the decision is local.** The dispatcher sniffs once and hands every converter the same vetted hints. Each converter only answers "is this mine?".
- **Built-ins get no back door.** `enable_builtins()` goes through the public `register_converter()`. So a plugin can do anything a built-in does, including replacing one by priority alone. No unregister API is needed, and the built-in stays as a fallback if the shadow raises.
- **Failure is local; recovery is central.** A converter just raises. The dispatcher decides whether someone else can help, and which error the caller sees.

## The price

- **Silent fallbacks.** In scene 5 the user got raw YAML and no warning: the `MissingDependencyException` was discarded because PlainText succeeded. markitdown behaves the same way.
- **The first success ends the search, even when it's wrong.** Scene 4 recovers only because plain text *fails* on zip bytes. markitdown's `PlainTextConverter` never refuses: without a charset it takes `charset_normalizer`'s best guess, so there the hinted guess "succeeds" and the sniffed one is never tried.
- **Priorities are global numbers, coordinated by convention.** Two plugins that both shadow `.csv` at -1.0 are ordered by registration, which means by entry-point load order.
- **Everything must be seekable.** Rewinding between attempts needs a seekable stream, so a non-seekable input (and, in markitdown, every HTTP response) is read fully into memory first.

## What the toy leaves out

`file:` and `http(s):` URIs and `convert_response()` (more doors, same shape); magika (an ML
model where `_sniff()` stands); about 16 more converters, several of which render to HTML and
reuse `HtmlConverter` (DOCX, EPUB, XLSX, PPTX); global options such as `llm_client` that the
dispatcher injects into every converter's `**kwargs`; deprecated aliases (`file_extension=`,
`url=`, `text_content`); `__plugin_interface_version__`, which plugins declare and the core
doesn't check yet; the `markitdown` CLI. None of them change the shape.

## Where you meet it

Apache Tika (`AutoDetectParser`: detect the type from magic bytes and name, then dispatch to
a parser registry). Pillow's `Image.open` (each format plugin registers an `_accept(prefix)`
check, tried in order). pydicom's pixel-data decoders (several per transfer syntax, tried in
order, each available only if its optional library, such as GDCM, pylibjpeg or Pillow, is
installed). pytest plugins (the `pytest11` entry-point group).

## Exercises

1. Write a `ShoutingTextConverter` for `.txt` and register it on a fresh `MarkItDown()` at
   priority 10, the same as PlainText. Why does it win? Change `insert(0, …)` to `append(…)`
   in `register_converter()` and try again.
2. Make `PlainTextConverter.convert` decode with `errors="replace"`, which is closer to
   markitdown. Rerun scene 4. What does the user get now, and why is guess 2 never tried?
3. Give a converter an `accepts()` that reads 4 bytes and doesn't seek back. What catches it?
   What would go wrong for the *next* converter if nothing did?
4. Add a `JsonConverter` as a second plugin: a new module with `register_converters()`, one
   more line in the `[project.entry-points."minimd.plugin"]` table, then `uv sync`. What did
   you change in `minimd/`? (Nothing.)
5. Convert a one-column CSV (`name\nada\nalan\n`) with plugins enabled and read the trace.
   `csv.Sniffer` can't find a delimiter, so the shadow raises. Who answers instead, and what
   does that tell you about shadowing versus replacing?

[r-stream]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_stream_info.py
[r-base]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_base_converter.py#L42-L105
[r-exc]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_exceptions.py
[r-load]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L65-L82
[r-builtins]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L181-L204
[r-enable]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L232-L250
[r-doors]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L252-L536
[r-convert]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L538-L631
[r-invariant]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L598-L614
[r-normalize]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L616-L622
[r-register]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L641-L671
[r-guesses]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/_markitdown.py#L673-L772
[r-docx-guard]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/converters/_docx_converter.py#L13-L21
[r-docx-raise]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/converters/_docx_converter.py#L65-L77
[r-zip]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown/src/markitdown/converters/_zip_converter.py#L61-L107
[r-sample]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown-sample-plugin/src/markitdown_sample_plugin/_plugin.py#L25-L31
[r-sample-ep]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown-sample-plugin/pyproject.toml#L40-L41
[r-ocr]: https://github.com/microsoft/markitdown/blob/a51f725d7ff4cdfe3bb6ad2ce2c04d98bf5f1f00/packages/markitdown-ocr/src/markitdown_ocr/_plugin.py#L52-L68
