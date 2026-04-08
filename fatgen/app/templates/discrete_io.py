"""Discrete I/O check template."""
from __future__ import annotations
from .base_template import TestTemplate


class DiscreteIOTemplate(TestTemplate):

    def get_test_points(self) -> list[dict]:
        from ..models.tag import IOType
        tag = self.tag
        if tag.io_type == IOType.DI:
            return [
                {"state": "OPEN (0)", "field_condition": "Contact open / deenergized",
                 "plc_expected": "FALSE (0)", "hmi_expected": "Inactive", "pass_fail": ""},
                {"state": "CLOSED (1)", "field_condition": "Contact closed / energized",
                 "plc_expected": "TRUE (1)", "hmi_expected": "Active", "pass_fail": ""},
            ]
        else:  # DO
            return [
                {"state": "OFF (0)", "field_condition": "Output deenergized",
                 "plc_expected": "FALSE (0)", "hmi_expected": "Off", "field_verified": "", "pass_fail": ""},
                {"state": "ON (1)", "field_condition": "Output energized",
                 "plc_expected": "TRUE (1)", "hmi_expected": "On", "field_verified": "", "pass_fail": ""},
            ]

    def get_steps(self) -> list[dict]:
        from ..models.tag import IOType
        tag = self.tag
        if tag.io_type == IOType.DI:
            return [
                {
                    "step": 1,
                    "action": f"Confirm {tag.name} wired to PLC address {tag.address}. Apply power to field device.",
                    "expected": "No wiring faults. Channel OK in diagnostic.",
                    "result": "",
                },
                {
                    "step": 2,
                    "action": f"Open / deenergize field contact. Verify PLC address {tag.address} = FALSE (0).",
                    "expected": "PLC reads 0. HMI shows inactive state.",
                    "result": "",
                },
                {
                    "step": 3,
                    "action": f"Close / energize field contact. Verify PLC address {tag.address} = TRUE (1).",
                    "expected": "PLC reads 1. HMI shows active state.",
                    "result": "",
                },
            ]
        else:
            return [
                {
                    "step": 1,
                    "action": f"Confirm {tag.name} wired to PLC output address {tag.address}. Field device connected.",
                    "expected": "No wiring faults. Output channel OK.",
                    "result": "",
                },
                {
                    "step": 2,
                    "action": f"Force PLC output {tag.address} = FALSE (0). Verify field device deenergizes.",
                    "expected": "Field device off. Current draw = 0.",
                    "result": "",
                },
                {
                    "step": 3,
                    "action": f"Force PLC output {tag.address} = TRUE (1). Verify field device energizes.",
                    "expected": "Field device on. Correct current draw measured.",
                    "result": "",
                },
                {
                    "step": 4,
                    "action": "Remove force. Confirm output returns to program-controlled state.",
                    "expected": "Output follows PLC logic. No forced state.",
                    "result": "",
                },
            ]
