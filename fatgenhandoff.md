# FATGen — Claude Code Handoff Specification
**Factory Acceptance Test Document Generator**
**Version:** 0.9 — Phase 1 Build Spec  
**Date:** 2024-11-15  
**Target Platform:** Python 3.11+ / Tkinter UI / python-docx output

---

## 1. Project Summary

FATGen is a document generation tool for PLC-based Factory Acceptance Tests (FAT) in the heavy process industry (chemical, refining, petrochemical). It ingests an instrument tag list and I/O tree from a PLC IDE, allows an engineer to configure test types per tag, and renders structured Word documents (.docx) that field technicians and client witnesses execute and sign during the FAT.

The core insight: FAT documents are structurally repetitive but vary in tag names, addresses, engineering units, spans, alarm setpoints, and instrument types. This tool separates template logic from tag data.

**Primary customers:** Systems integrators performing FATs for clients like BASF, ExxonMobil, Shell, Marathon, Dow.

---

## 2. Architecture Overview

```
fatgen/
├── main.py                  # Entry point, Tkinter root window
├── app/
│   ├── ui/
│   │   ├── main_window.py   # Top-level layout (notebook/tabs)
│   │   ├── project_panel.py # Project setup form
│   │   ├── import_panel.py  # CSV import + tag table view
│   │   ├── config_panel.py  # Test configuration UI
│   │   └── preview_panel.py # Document preview (HTML webview or text)
│   ├── models/
│   │   ├── project.py       # Project, Client, Engineer dataclasses
│   │   ├── tag.py           # Tag, IOChannel, Instrument dataclasses
│   │   └── test_config.py   # TestCase, TestType, TestParameter
│   ├── importers/
│   │   ├── base.py          # Abstract importer interface
│   │   ├── s7_csv.py        # Siemens S7-1500 TIA Portal CSV parser
│   │   └── ab_csv.py        # Allen-Bradley RSLogix/Studio 5000 CSV (Phase 2)
│   ├── templates/
│   │   ├── base_template.py # Abstract TestTemplate class
│   │   ├── ai_scaling.py    # Analog Input 5-point scaling
│   │   ├── ao_scaling.py    # Analog Output 5-point scaling
│   │   ├── alarm_verify.py  # HH/H/L/LL alarm verification
│   │   ├── motor_logic.py   # Motor starter logic test
│   │   ├── interlock.py     # Interlock / SIS trip test
│   │   ├── discrete_io.py   # Discrete I/O check
│   │   └── custom_logic.py  # User-defined logic test
│   ├── renderer/
│   │   ├── docx_renderer.py # python-docx document builder
│   │   └── styles.py        # Document styles, fonts, table formats
│   └── logic/
│       └── evaluator.py     # Phase 2: truth-table / dependency evaluator
├── tests/
│   └── test_*.py
├── requirements.txt
└── README.md
```

---

## 3. Data Model

### 3.1 Tag

```python
@dataclass
class Tag:
    name: str                    # "FT-101"
    description: str             # "Reactor Feed Flow"
    io_type: IOType              # Enum: AI, AO, DI, DO
    address: str                 # S7: "%IW64" | AB: "I:0/0"
    rack: int
    slot: int
    channel: int
    instrument_model: str        # "Rosemount 3051 CD"
    span_low: float              # 0.0
    span_high: float             # 500.0
    eng_units: str               # "GPM"
    signal_type: SignalType      # Enum: mA_4_20, V_1_5, V_0_10
    adc_resolution: int          # 16 (bits) → max counts 27648 for S7
    sqrt_extraction: SqrtLoc     # Enum: CONTROLLER, TRANSMITTER, NONE
    dp_range_low: float          # 0.0
    dp_range_high: float         # 250.0  (inches H2O)
    dp_units: str                # "in H2O"
    alarms: list[AlarmSetpoint]  # list of AlarmSetpoint
    plc_alarm_bits: dict         # {"HH": "%M100.3", "H": "%M100.2", ...}
    interlock_tags: list[str]    # tags that interlock this one
    notes: str

@dataclass
class AlarmSetpoint:
    level: str        # "HH", "H", "L", "LL"
    setpoint: float
    deadband: float
    plc_bit: str      # "%M100.3"

class IOType(Enum):
    AI = "Analog Input"
    AO = "Analog Output"
    DI = "Discrete Input"
    DO = "Discrete Output"

class SqrtLoc(Enum):
    CONTROLLER = "Controller (PLC)"
    TRANSMITTER = "Transmitter (HART)"
    NONE = "Not Applicable"
```

### 3.2 Project

```python
@dataclass
class Project:
    project_number: str       # "BASF-HOU-2024-047"
    project_name: str         # "Ethylene Oxide Unit FAT"
    client_name: str          # "BASF Corporation"
    client_site: str          # "Freeport, TX"
    si_company: str           # "ControlPath Inc."
    engineer: str
    revision: str             # "A"
    revision_date: str        # "2024-11-15"
    platform: PLCPlatform     # Enum: SIEMENS_S7_1500, AB_CONTROLLOGIX, ...
    plc_model: str            # "CPU 1515-2 PN"
    tags: list[Tag]
    test_cases: list[TestCase]

class PLCPlatform(Enum):
    SIEMENS_S7_1500 = "Siemens S7-1500"
    SIEMENS_S7_300  = "Siemens S7-300/400"
    AB_CONTROLLOGIX = "Allen-Bradley ControlLogix"
    AB_COMPACTLOGIX = "Allen-Bradley CompactLogix"
```

### 3.3 TestCase

```python
@dataclass
class TestCase:
    test_id: str              # "DOC-FAT-2024-047-003"
    test_type: TestType       # Enum
    tag: Tag                  # reference to tag being tested
    doc_number: str           # auto-generated
    preconditions: list[str]  # free text or ref to other TestCase IDs
    depends_on: list[str]     # TestCase IDs whose state this test references
    include_alarms: bool
    include_hart: bool
    include_adc_counts: bool
    witness_blocks: int       # number of signature blocks (1–3)
    notes: str

class TestType(Enum):
    AI_SCALING     = "Analog Input Scaling"
    AO_SCALING     = "Analog Output Scaling"
    ALARM_VERIFY   = "Alarm Setpoint Verification"
    MOTOR_LOGIC    = "Motor Starter Logic"
    INTERLOCK      = "Interlock / SIS Verification"
    DISCRETE_IO    = "Discrete I/O Check"
    CUSTOM         = "Custom Logic Test"
```

---

## 4. Importer: Siemens S7-1500 (TIA Portal CSV)

### 4.1 Expected CSV Column Format

TIA Portal tag export produces:

```
Name,Path,Data Type,Logical Address,Comment
FT_101,Default tag table,Int,%IW64,Reactor Feed Flow Raw
FT_101_EU,Default tag table,Real,%MD100,Reactor Feed Flow GPM
P201_START,Default tag table,Bool,%Q0.0,Feed Pump Start
P201_RUN,Default tag table,Bool,%I1.0,Feed Pump Run Feedback
```

**Also supported:** I/O device configuration export (CSV from device view) which adds rack/slot/channel columns.

### 4.2 Address Parsing Rules — S7-1500

| Prefix | Type | Notes |
|--------|------|-------|
| `%IW`  | Analog Input (word) | 16-bit signed, max 27648 = 100% |
| `%QW`  | Analog Output (word) | 16-bit |
| `%I`   | Discrete Input (bit) | `%I0.0` = rack 0, byte 0, bit 0 |
| `%Q`   | Discrete Output (bit) | |
| `%MW`  | Memory word | |
| `%M`   | Memory bit | alarm bits live here |
| `%DB`  | Data block | `%DB10.DBX0.0` = DB10, bool offset 0.0 |

Parse address string with regex:
```python
import re
AI_PATTERN  = re.compile(r'%IW(\d+)')
AO_PATTERN  = re.compile(r'%QW(\d+)')
DI_PATTERN  = re.compile(r'%I(\d+)\.(\d+)')
DO_PATTERN  = re.compile(r'%Q(\d+)\.(\d+)')
MEM_PATTERN = re.compile(r'%M(\d+)\.(\d+)')
DB_PATTERN  = re.compile(r'%DB(\d+)\.DBX(\d+)\.(\d+)')
```

### 4.3 Auto-mapping Heuristics

The importer should attempt to auto-detect:
- Tags ending in `_EU`, `_PV`, `_SP` are likely linked to a raw AI tag
- Tag pairs like `P201_START` / `P201_RUN` / `P201_FAULT` → motor group
- Tags with `_HH`, `_H`, `_L`, `_LL` suffixes or comments → alarm bits

Group these automatically and present to the engineer for confirmation in the UI.

---

## 5. Template Engine

### 5.1 Abstract Base

```python
class TestTemplate(ABC):
    def __init__(self, test_case: TestCase, project: Project):
        self.tc = test_case
        self.project = project

    @abstractmethod
    def get_test_points(self) -> list[dict]:
        """Return list of test point row dicts for the scaling table."""
        pass

    @abstractmethod
    def get_steps(self) -> list[dict]:
        """Return ordered list of {step, action, expected, pass_field} dicts."""
        pass

    def get_doc_metadata(self) -> dict:
        """Returns header fields: doc_number, client, tag, address, etc."""
        pass
```

### 5.2 Analog Input Scaling — Key Calculations

For a **5-point check** on a 4–20 mA / 16-bit S7-1500 AI:

```python
PERCENTAGES = [0, 25, 50, 75, 100]
S7_MAX_COUNTS = 27648  # 16-bit signed, S7 convention

def calc_test_points(tag: Tag) -> list[dict]:
    points = []
    for pct in PERCENTAGES:
        fraction = pct / 100.0
        mA = 4.0 + fraction * 16.0
        vdc_250ohm = mA * 0.250           # across 250Ω burden resistor
        counts = round(fraction * S7_MAX_COUNTS)

        if tag.sqrt_extraction == SqrtLoc.CONTROLLER:
            # Raw DP input — linear. EU is √(fraction) * span
            dp_sim = fraction * tag.dp_range_high
            eu_expected = math.sqrt(fraction) * tag.span_high
        elif tag.sqrt_extraction == SqrtLoc.TRANSMITTER:
            # Instrument outputs √DP as mA. EU is linear.
            dp_sim = (fraction ** 2) * tag.dp_range_high  # DP needed to get linear flow out
            eu_expected = fraction * tag.span_high
        else:
            dp_sim = None
            eu_expected = fraction * (tag.span_high - tag.span_low) + tag.span_low

        points.append({
            "pct": pct,
            "mA_expected": round(mA, 3),
            "vdc_expected": round(vdc_250ohm, 3),
            "counts_expected": counts,
            "dp_sim": round(dp_sim, 2) if dp_sim is not None else "N/A",
            "eu_expected": round(eu_expected, 2),
        })
    return points
```

### 5.3 Alarm Verification Template

For each alarm level in tag.alarms, produce a row with:
- configured setpoint (from tag data)
- simulation target value (setpoint + margin to confirm activation)
- PLC bit address
- deadband
- reset confirmation field

### 5.4 Motor Starter Logic Template

Fixed 7-step sequence (see demo document for exact verbiage). Dynamic fields:
- Tag names for START (`%Q`), RUN (`%I`), FAULT (`%I`), LATCH (`%M`)
- HOA DB address
- Interlock tag name and bit address
- Any referenced downstream device (e.g., isolation valve DO tag)

### 5.5 Custom Logic Template

User provides:
- A list of precondition rows: `{tag, operator, value, description}`
- A list of assertion rows: `{tag, expected_value, description}`
- Can reference `TestCase.test_id` of a previous test as a precondition group

---

## 6. Document Renderer (python-docx)

### 6.1 Document Structure

Each generated document follows this section order:
1. **Header** — company logo block, doc number, revision, date, page
2. **Title block** — centered, ALLCAPS, test type + tag
3. **Info table** — 2-column key/value: client, tag, address, instrument, span, etc.
4. **Notes** — italic, left-bordered, for variant-specific instructions (e.g., sqrt note)
5. **Test section** — numbered section heading + test table
6. **Step table** (if applicable) — numbered steps with pass/fail boxes
7. **Signature block** — 3-column: SI engineer, client rep, instrument tech

### 6.2 Styles

```python
STYLES = {
    "section_heading": {
        "font": "Arial", "size": 9, "bold": True, "allcaps": True,
        "shading": "222222", "color": "FFFFFF"
    },
    "table_header": {
        "font": "Arial", "size": 8, "bold": True, "allcaps": True,
        "shading": "555555", "color": "FFFFFF", "alignment": "CENTER"
    },
    "table_cell": {"font": "Arial", "size": 9, "alignment": "CENTER"},
    "table_cell_label": {"font": "Arial", "size": 9, "bold": True, "shading": "EEEEEE"},
    "doc_title": {"font": "Arial", "size": 13, "bold": True, "allcaps": True},
    "company_name": {"font": "Arial", "size": 14, "bold": True},
    "note_text": {"font": "Arial", "size": 8, "italic": True, "color": "555555"},
    "info_key": {"font": "Arial", "size": 9, "bold": True, "shading": "F0F0F0"},
    "info_val": {"font": "Arial", "size": 9},
}
```

### 6.3 Pass/Fail Input Fields

In the rendered .docx, pass/fail fields should be rendered as **empty table cells** with a light gray border — they are filled in by hand during the FAT. Do NOT use form fields (they cause compatibility issues). A narrow fixed-width column (1.5 cm) with a thin border is sufficient.

### 6.4 Document Numbering

Auto-generated format:
```
DOC-FAT-{project_number}-{sequence:03d}
```

Sequence is assigned in test execution order.

---

## 7. Platform Addressing Reference

### Siemens S7-1500

| Signal | Address Format | ADC Full Scale | Notes |
|--------|---------------|----------------|-------|
| AI 16-bit | `%IW64` | 27648 counts | Byte offset, not channel number |
| AO 16-bit | `%QW80` | 27648 counts | |
| DI | `%I0.0` | — | Byte.Bit |
| DO | `%Q0.0` | — | |
| Alarm bit | `%M100.3` | — | Byte.Bit |
| HOA / state | `%DB10.DBX0.0` | — | DataBlock.Bool |

### Allen-Bradley ControlLogix (Phase 2)

| Signal | Tag Format | Notes |
|--------|-----------|-------|
| AI | `Local:3:I.Ch0Data` | Module-qualified tag |
| AO | `Local:3:O.Ch0Data` | |
| DI | `Local:1:I.Data.0` | |
| DO | `Local:1:O.Data.0` | |
| Alarm | `FT101_HH_ALM` | Named tags, no fixed schema |
| ADC full scale | 32767 (INT) or 4095 (older) | Module-dependent |

---

## 8. Phase 1 Build Order

### Step 1: Core data model
- `models/tag.py`, `models/project.py`, `models/test_config.py`
- All dataclasses + enums
- JSON serialization (save/load project)

### Step 2: S7-1500 CSV Importer
- `importers/s7_csv.py`
- Parse TIA Portal tag export CSV
- Address regex parsing → IOType detection
- Auto-group motor tag sets
- Return `list[Tag]`

### Step 3: Template Engine — first 3 templates
- `templates/ai_scaling.py` (with sqrt variant)
- `templates/alarm_verify.py`
- `templates/motor_logic.py`

### Step 4: python-docx Renderer
- `renderer/docx_renderer.py`
- Build header, info table, test table, step table, sig block
- Apply styles from `renderer/styles.py`
- Export single test → .docx
- Export all tests → single combined .docx with page breaks

### Step 5: Tkinter UI Shell
- `ui/main_window.py` — notebook with 4 tabs
  - Tab 1: Project Setup (form fields)
  - Tab 2: Import (file picker + tag table with ttk.Treeview)
  - Tab 3: Test Configuration (list of tests, add/remove/configure)
  - Tab 4: Generate (export options, output path)
- Connect UI to model and renderer
- Save/load project as JSON

---

## 9. Phase 2 — Logic Evaluator (Deferred)

Lightweight truth-table evaluator for interlock and custom logic tests.

```python
@dataclass
class Precondition:
    tag_name: str
    operator: str        # "==", ">", "<", ">=", "<="
    value: float | bool
    description: str

@dataclass
class Assertion:
    tag_name: str
    expected_value: float | bool
    tolerance: float     # for analog assertions
    description: str

@dataclass
class LogicTest:
    preconditions: list[Precondition]
    assertions: list[Assertion]
    depends_on: list[str]   # TestCase IDs — state is imported as preconditions

def evaluate(logic_test: LogicTest, simulated_state: dict) -> list[AssertionResult]:
    """
    Given a dict of {tag_name: current_value}, evaluate all assertions.
    Returns list of {assertion, passed, actual_value}.
    No PLC connection needed — state is manually entered or imported.
    """
```

---

## 10. Dependencies

```
python >= 3.11
python-docx >= 1.1.0
tkinter (stdlib)
pandas >= 2.0       # CSV import
openpyxl >= 3.1     # xlsx support (future)
dataclasses-json    # JSON serialization
pytest              # testing
```

---

## 11. Key Design Decisions

1. **No PLC connection required.** All test data is manually entered or simulated. The tool generates paper documents — it does not execute tests against a live controller.

2. **Templates own the verbiage.** The exact wording of test steps lives in the template class, not in the UI. This ensures consistency across all generated documents.

3. **Tags drive everything.** Importing the tag list is the first and most critical step. All test configuration flows from tag metadata.

4. **Platform is a project-level setting.** It affects address formatting and ADC full-scale value but not the test structure. The same template generates correct documents for S7 or AB by querying `project.platform`.

5. **JSON project files.** Save/load the entire project (tags + test configurations) as a single `.fatgen` JSON file. This allows projects to be shared between engineers.

6. **Output is .docx only.** PDF export is secondary (convert via Word or LibreOffice). The priority is an editable, signable Word document.

---

## 12. Not In Scope (Phase 1)

- Live PLC OPC-UA or Ethernet/IP connection
- HMI screen validation
- Allen-Bradley native `.L5X` parsing (CSV only)
- PDF generation
- Multi-user / networked project sharing
- Audit trail / version history

---

*End of handoff document. Questions: refer to demo HTML for UI layout intent.*