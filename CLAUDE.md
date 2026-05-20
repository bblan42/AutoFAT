# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FATGen is a Flask-based Phase 1 build of a Factory Acceptance Test document generator. It ingests Siemens S7-1500 (TIA Portal) CSV tag exports, lets an engineer configure test cases per tag, and renders structured `.docx` documents via `python-docx`. There is no PLC connection — the tool produces paper documents that are filled in by hand during the FAT.

The aspirational spec lives in `fatgenhandoff.md` (v0.9). The handoff doc's directory tree, scope (Tkinter-first), and dependency list (pandas/openpyxl/pytest/dataclasses-json) are **out of date** — the real app is Flask-first and depends only on `flask>=3.0` and `python-docx>=1.1.0` (see `requirements.txt`). Treat the handoff as intent/calculations reference, not ground truth.

## Run

```bash
pip install -r requirements.txt
python main.py --web                    # default: Flask on 0.0.0.0:5000
python main.py --web --port 8080 --debug
python main.py --desktop                # Tkinter stub only — shows "Coming Soon"
```

There is **no test runner, linter, or build step configured**. `tests/` contains only `sample_tags_s7_1500.csv` — a fixture for manual import testing, not a pytest suite. Don't claim tests pass without setting up the framework first.

## Architecture

Entry point `main.py` dispatches to either `fatgen.app.ui.web.routes:app` (Flask) or `fatgen.app.ui.desktop.main_window:run` (stub).

Pipeline: **CSV → importer → `Tag` list → `TestCase` configs → `TestTemplate` → `DocxRenderer` → `.docx` bytes**.

```
fatgen/app/
├── models/          # Plain dataclasses + Enums, all with to_dict/from_dict
│   ├── tag.py           Tag, IOType, SignalType, SqrtLoc, AlarmSetpoint
│   ├── project.py       Project, PLCPlatform (knows adc_max_counts)
│   ├── test_config.py   TestCase, TestType
│   └── logic.py         LogicNetwork/Rung/Element for the ladder builder
├── importers/       # BaseImporter ABC + S7CSVImporter (regex address parser)
├── templates/       # FAT test templates — NOT Jinja. TestTemplate subclasses
│   │                  produce get_test_points() + get_steps() dicts.
│   ├── ai_scaling.py    5-point AI check, sqrt extraction variants
│   ├── alarm_verify.py  HH/H/L/LL setpoint verification
│   ├── motor_logic.py   Fixed 7-step motor starter sequence
│   └── discrete_io.py
├── renderer/        # python-docx builders (tables only, no images)
│   ├── docx_renderer.py Single & combined doc rendering, TestType→Template map
│   ├── ladder_docx.py   Ladder-diagram + minimap rendering (LogicNetwork)
│   └── styles.py        Shading/border/font helpers for cells
└── ui/
    ├── web/         # Flask app + Jinja templates (web/templates/*.html)
    └── desktop/     # Tkinter stub only
```

### Two "templates" directories — don't confuse them

- `fatgen/app/templates/` holds **FAT test templates** (Python classes producing test step/point dicts).
- `fatgen/app/ui/web/templates/` holds **Jinja HTML templates** that Flask renders.

Both are imported regularly; check the path before assuming.

### TestType → Template dispatch

`renderer/docx_renderer.py:_template_for` maps `TestType` enums to template classes. `AO_SCALING`, `INTERLOCK`, and `CUSTOM` currently **fall back to `AIScalingTemplate`** — this is a known Phase 1 placeholder, not a bug. When adding a real implementation, add the class and update the mapping.

### Session/state storage

`ui/web/routes.py` keeps everything in a module-level `_PROJECTS: dict[str, dict]` keyed by a per-session UUID. Keys used: `<pid>` (project), `<pid>_tests` (test cases), `<pid>_networks` (logic networks). This is in-memory only — restart drops all state. Project save/load goes through `/project/export` and `/project/import-file` which read/write a single `.fatgen` JSON file (= `{project, test_cases}` dict).

### Model serialization conventions

Every dataclass exposes `to_dict()` and `from_dict()`. Enums serialize by `.name` (e.g. `"AI_SCALING"`), not `.value`. When adding fields to a model, update **both** methods and provide a sensible default in `from_dict` so older `.fatgen` files keep loading.

### S7 importer specifics (`importers/s7_csv.py`)

- Address regexes are S7-specific: `%IW`, `%QW`, `%I`, `%Q`, `%M`, `%DB.DBX`.
- Post-processing **mutates the tag list**:
  - Tags ending `_HH/_H/_L/_LL` whose I/O type is `MEM/DB/DI` are folded into the parent tag's `alarms` list and removed from the output.
  - Tags ending `_EU/_PV/_SP/_CV` are dropped (derived values, not test subjects).
- `parse_text(str)` is the path used by the web upload; `parse(filepath)` is for CLI/desktop.

### Doc numbering & ADC counts

- Format: `DOC-FAT-{project_number}-{seq:03d}`, assigned in current test-case order by `_assign_doc_numbers` at generation time.
- ADC full-scale comes from `Project.adc_max_counts()`: **27648** for Siemens, **32767** for Allen-Bradley. AI scaling templates depend on this — don't hardcode.

### Pass/fail cells

Rendered as plain shaded `.docx` table cells with thin borders (`apply_pass_fail_cell` in `renderer/styles.py`). **Do not** introduce Word form fields — they cause compatibility issues across Word versions and were explicitly avoided.

## Conventions when adding code

- New test types: add a `TestTemplate` subclass under `fatgen/app/templates/`, register it in `_template_for`, and add the enum to `TestType`.
- New importers: subclass `BaseImporter` (`importers/base.py`) and instantiate from a new web route — there is no plugin registry yet.
- New Flask routes: follow the existing `_get_project()` / `_save_project()` helper pattern; don't introduce a database.
- HTML: extend `ui/web/templates/base.html` and use the existing `--bg/--amber/--mono` CSS vars. Styling is inline in `base.html` (no `static/` directory exists despite `static_folder="static"` in `routes.py`).
