"""Alarm Setpoint Verification template."""
from __future__ import annotations
from .base_template import TestTemplate


class AlarmVerifyTemplate(TestTemplate):

    def get_test_points(self) -> list[dict]:
        tag = self.tag
        span = tag.span_high - tag.span_low
        rows = []

        for alarm in tag.alarms:
            # Margin: push 2% of span past the setpoint to confirm activation
            margin = span * 0.02
            if alarm.level in ("HH", "H"):
                sim_value = round(alarm.setpoint + margin, 2)
                reset_value = round(alarm.setpoint - alarm.deadband - margin, 2)
            else:  # L, LL
                sim_value = round(alarm.setpoint - margin, 2)
                reset_value = round(alarm.setpoint + alarm.deadband + margin, 2)

            rows.append({
                "alarm_level": alarm.level,
                "setpoint": alarm.setpoint,
                "deadband": alarm.deadband,
                "plc_bit": alarm.plc_bit,
                "sim_value": sim_value,
                "reset_value": reset_value,
                "alarm_activated": "",   # hand-filled
                "alarm_reset": "",
                "pass_fail": "",
            })

        return rows

    def get_steps(self) -> list[dict]:
        tag = self.tag
        steps = [
            {
                "step": 1,
                "action": f"Confirm {tag.name} is in service and reading a stable process value within normal range.",
                "expected": "No active alarms on tag.",
                "result": "",
            },
            {
                "step": 2,
                "action": "Connect mA loop calibrator. Confirm 4–20 mA range and EU scaling match instrument data sheet.",
                "expected": "Loop reading matches tag data.",
                "result": "",
            },
        ]

        for i, alarm in enumerate(tag.alarms):
            span = tag.span_high - tag.span_low
            margin = span * 0.02
            if alarm.level in ("HH", "H"):
                sim_val = round(alarm.setpoint + margin, 2)
                reset_val = round(alarm.setpoint - alarm.deadband - margin, 2)
                direction = "above"
            else:
                sim_val = round(alarm.setpoint - margin, 2)
                reset_val = round(alarm.setpoint + alarm.deadband + margin, 2)
                direction = "below"

            steps.append({
                "step": len(steps) + 1,
                "action": (
                    f"Simulate {alarm.level} alarm: drive signal to {sim_val} {tag.eng_units} "
                    f"({direction} setpoint of {alarm.setpoint} {tag.eng_units}). "
                    f"Verify PLC bit {alarm.plc_bit} goes TRUE."
                ),
                "expected": f"PLC bit {alarm.plc_bit} = TRUE. Alarm annunciated on HMI.",
                "result": "",
            })
            steps.append({
                "step": len(steps) + 1,
                "action": (
                    f"Reset {alarm.level} alarm: drive signal to {reset_val} {tag.eng_units} "
                    f"(past deadband of {alarm.deadband} {tag.eng_units}). "
                    f"Verify PLC bit {alarm.plc_bit} goes FALSE."
                ),
                "expected": f"PLC bit {alarm.plc_bit} = FALSE. Alarm clears on HMI.",
                "result": "",
            })

        steps.append({
            "step": len(steps) + 1,
            "action": "Remove calibrator. Restore loop to normal operating condition.",
            "expected": "No active alarms. Instrument returns to live reading.",
            "result": "",
        })

        return steps
