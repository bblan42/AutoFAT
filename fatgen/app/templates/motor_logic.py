"""Motor Starter Logic test template — fixed 7-step sequence."""
from __future__ import annotations
from .base_template import TestTemplate


class MotorLogicTemplate(TestTemplate):
    """
    Expects tag groups detected by the importer.
    tag.name         = base device tag (e.g. "P201")
    tag.notes        = JSON string or structured field for motor-specific addresses:
                       start_tag, run_tag, fault_tag, stop_tag, hoa_db, interlock_tag
    The renderer pulls motor-specific fields from tc.notes or tag.notes.
    """

    def _motor_tags(self) -> dict:
        """Extract motor sub-tag addresses from notes or use sensible defaults."""
        base = self.tag.name
        return {
            "start":     f"{base}_START",
            "stop":      f"{base}_STOP",
            "run":       f"{base}_RUN",
            "fault":     f"{base}_FAULT",
            "hoa_db":    f"DB_HOA_{base}",
            "interlock": self.tag.interlock_tags[0] if self.tag.interlock_tags else "—",
        }

    def get_test_points(self) -> list[dict]:
        # Motor logic test uses steps only; no scaling table
        return []

    def get_steps(self) -> list[dict]:
        tag = self.tag
        mt = self._motor_tags()
        base = tag.name

        steps = [
            {
                "step": 1,
                "action": (
                    f"Confirm {base} is in HAND mode via HOA selector ({mt['hoa_db']}). "
                    f"Verify all safety interlocks permissive. Isolate equipment per site procedures."
                ),
                "expected": "HOA = HAND. No active interlock trips. Equipment isolated.",
                "result": "",
            },
            {
                "step": 2,
                "action": (
                    f"Issue START command via HMI / {mt['start']} output bit. "
                    f"Verify RUN feedback ({mt['run']}) goes TRUE within 5 seconds."
                ),
                "expected": f"{mt['run']} = TRUE. Motor running indication on HMI.",
                "result": "",
            },
            {
                "step": 3,
                "action": (
                    f"Issue STOP command via HMI / {mt['stop']} output bit. "
                    f"Verify RUN feedback ({mt['run']}) goes FALSE."
                ),
                "expected": f"{mt['run']} = FALSE. Motor stopped indication on HMI.",
                "result": "",
            },
            {
                "step": 4,
                "action": (
                    f"Switch HOA to AUTO mode. Verify motor does not start without auto command. "
                    f"Issue auto start via interlock/sequence logic. Verify {mt['run']} = TRUE."
                ),
                "expected": "Motor starts only on valid auto command. No spurious start.",
                "result": "",
            },
            {
                "step": 5,
                "action": (
                    f"With motor running (AUTO), simulate interlock trip: "
                    f"force {mt['interlock']} to trip state. "
                    f"Verify motor stops and FAULT is latched."
                ),
                "expected": f"Motor stops. {mt['fault']} = TRUE. Fault latched on HMI.",
                "result": "",
            },
            {
                "step": 6,
                "action": (
                    f"Clear interlock condition. Issue RESET command. "
                    f"Verify fault clears ({mt['fault']} = FALSE) and motor is ready to restart."
                ),
                "expected": f"{mt['fault']} = FALSE. No active faults. Motor ready.",
                "result": "",
            },
            {
                "step": 7,
                "action": (
                    f"Restore {base} to normal operating HOA position. "
                    f"Confirm with client representative and document final state."
                ),
                "expected": "Equipment in normal service state. Client confirmed.",
                "result": "",
            },
        ]

        return steps
