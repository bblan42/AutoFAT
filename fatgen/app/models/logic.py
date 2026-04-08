"""
Logic builder data model.

A LogicNetwork represents a complete section of PLC logic (e.g., "Feed Pump Start Logic").
It contains one or more LogicRungs, each holding a sequence of LogicElements.
A TestCase references a LogicNetwork and specifies which rung indices are being tested —
this drives the minimap ("you are here") in both the UI and the .docx output.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ElementType(Enum):
    # Contacts (inputs)
    NO_CONTACT  = "NO"    # Normally Open  --| |--
    NC_CONTACT  = "NC"    # Normally Closed --|/|--
    # Coils (outputs)
    COIL        = "COIL"  # Output coil  --( )--
    SET_COIL    = "SET"   # Latch coil   --(S)--
    RESET_COIL  = "RST"   # Unlatch coil --(R)--
    # Timers
    TON         = "TON"   # On-delay timer
    TOF         = "TOF"   # Off-delay timer
    TP          = "TP"    # Pulse timer
    # Counters
    CTU         = "CTU"   # Count up
    CTD         = "CTD"   # Count down
    # Function block (generic)
    FB          = "FB"    # Named function block
    # Comparison / math
    CMP         = "CMP"   # Compare block (>, <, =, etc.)
    # Branch
    BRANCH_OPEN  = "BRO"  # Begin parallel branch
    BRANCH_CLOSE = "BRC"  # End parallel branch


@dataclass
class LogicElement:
    element_type: str        # ElementType.name
    tag: str = ""            # PLC tag name (e.g. "P201_RUN")
    address: str = ""        # PLC address (e.g. "%I1.0")
    label: str = ""          # Short display label (e.g. "RUN FB")
    parameter: str = ""      # Timer preset, counter limit, compare value, FB type name
    branch_id: int = 0       # 0 = main rung, 1+ = parallel branch index
    comment: str = ""        # Inline annotation shown below element

    def to_dict(self) -> dict:
        return {
            "element_type": self.element_type,
            "tag": self.tag,
            "address": self.address,
            "label": self.label,
            "parameter": self.parameter,
            "branch_id": self.branch_id,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LogicElement:
        return cls(**{k: d.get(k, "") for k in
                      ["element_type", "tag", "address", "label", "parameter", "comment",
                       "branch_id"]})


@dataclass
class LogicRung:
    rung_number: int          # 1-based, for display
    description: str = ""     # Short description of what this rung does
    elements: list[LogicElement] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rung_number": self.rung_number,
            "description": self.description,
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, d: dict) -> LogicRung:
        return cls(
            rung_number=d.get("rung_number", 1),
            description=d.get("description", ""),
            elements=[LogicElement.from_dict(e) for e in d.get("elements", [])],
        )


@dataclass
class LogicNetwork:
    """
    A complete named section of PLC logic.
    Contains all rungs for the section — the minimap renders all of them
    and highlights whichever rungs the current test covers.
    """
    network_id: str = ""
    name: str = ""                    # e.g. "Feed Pump P201 Start Logic"
    description: str = ""
    rungs: list[LogicRung] = field(default_factory=list)
    # Which rung numbers (1-based) are covered by the associated test
    test_rung_numbers: list[int] = field(default_factory=list)

    @property
    def total_rungs(self) -> int:
        return len(self.rungs)

    def to_dict(self) -> dict:
        return {
            "network_id": self.network_id,
            "name": self.name,
            "description": self.description,
            "rungs": [r.to_dict() for r in self.rungs],
            "test_rung_numbers": self.test_rung_numbers,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LogicNetwork:
        return cls(
            network_id=d.get("network_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            rungs=[LogicRung.from_dict(r) for r in d.get("rungs", [])],
            test_rung_numbers=d.get("test_rung_numbers", []),
        )
