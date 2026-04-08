from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .tag import Tag


class TestType(Enum):
    AI_SCALING   = "Analog Input Scaling"
    AO_SCALING   = "Analog Output Scaling"
    ALARM_VERIFY = "Alarm Setpoint Verification"
    MOTOR_LOGIC  = "Motor Starter Logic"
    INTERLOCK    = "Interlock / SIS Verification"
    DISCRETE_IO  = "Discrete I/O Check"
    CUSTOM       = "Custom Logic Test"


@dataclass
class TestCase:
    test_id: str = ""
    test_type: TestType = TestType.AI_SCALING
    tag_name: str = ""           # resolved against project.tags at render time
    doc_number: str = ""
    preconditions: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    include_alarms: bool = True
    include_hart: bool = False
    include_adc_counts: bool = True
    witness_blocks: int = 2
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_type": self.test_type.name,
            "tag_name": self.tag_name,
            "doc_number": self.doc_number,
            "preconditions": self.preconditions,
            "depends_on": self.depends_on,
            "include_alarms": self.include_alarms,
            "include_hart": self.include_hart,
            "include_adc_counts": self.include_adc_counts,
            "witness_blocks": self.witness_blocks,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TestCase:
        return cls(
            test_id=d.get("test_id", ""),
            test_type=TestType[d.get("test_type", "AI_SCALING")],
            tag_name=d.get("tag_name", ""),
            doc_number=d.get("doc_number", ""),
            preconditions=d.get("preconditions", []),
            depends_on=d.get("depends_on", []),
            include_alarms=d.get("include_alarms", True),
            include_hart=d.get("include_hart", False),
            include_adc_counts=d.get("include_adc_counts", True),
            witness_blocks=d.get("witness_blocks", 2),
            notes=d.get("notes", ""),
        )
