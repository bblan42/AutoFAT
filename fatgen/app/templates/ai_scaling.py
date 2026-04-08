"""Analog Input 5-point scaling template (with sqrt extraction variant)."""
from __future__ import annotations
import math
from ..models.tag import SqrtLoc
from .base_template import TestTemplate

PERCENTAGES = [0, 25, 50, 75, 100]


class AIScalingTemplate(TestTemplate):

    def get_test_points(self) -> list[dict]:
        tag = self.tag
        adc_max = self.project.adc_max_counts()
        points = []

        for pct in PERCENTAGES:
            fraction = pct / 100.0
            mA = 4.0 + fraction * 16.0
            vdc = round(mA * 0.250, 3)        # across 250 Ω burden
            counts = round(fraction * adc_max)

            if tag.sqrt_extraction == SqrtLoc.CONTROLLER:
                # Raw DP → PLC computes √
                dp_sim = fraction * tag.dp_range_high
                eu = math.sqrt(fraction) * tag.span_high if fraction > 0 else 0.0
            elif tag.sqrt_extraction == SqrtLoc.TRANSMITTER:
                # Transmitter outputs √DP as linear mA
                dp_sim = (fraction ** 2) * tag.dp_range_high
                eu = fraction * tag.span_high
            else:
                dp_sim = None
                eu = fraction * (tag.span_high - tag.span_low) + tag.span_low

            row = {
                "pct": pct,
                "mA_expected": round(mA, 3),
                "vdc_expected": vdc,
                "counts_expected": counts,
                "dp_sim": round(dp_sim, 2) if dp_sim is not None else "N/A",
                "eu_expected": round(eu, 2),
                "eu_actual": "",   # filled in by hand during FAT
                "pass_fail": "",
            }
            points.append(row)

        return points

    def get_steps(self) -> list[dict]:
        tag = self.tag
        sqrt_note = ""
        if tag.sqrt_extraction == SqrtLoc.CONTROLLER:
            sqrt_note = f"Square root extraction performed in PLC. Simulate raw DP signal at transmitter terminals."
        elif tag.sqrt_extraction == SqrtLoc.TRANSMITTER:
            sqrt_note = f"Square root extraction performed in transmitter (HART). Simulate using HART communicator."

        steps = [
            {
                "step": 1,
                "action": f"Verify instrument loop powered and no faults present for {tag.name}.",
                "expected": "No faults on PLC channel. Signal present.",
                "result": "",
            },
            {
                "step": 2,
                "action": f"Connect mA loop calibrator in series with {tag.name} at field junction box.",
                "expected": "Calibrator reads loop current.",
                "result": "",
            },
            {
                "step": 3,
                "action": f"Simulate 4.000 mA (0%). Verify PLC address {tag.address} reads 0 counts "
                          f"and HMI shows {tag.span_low} {tag.eng_units}. {sqrt_note}",
                "expected": f"PLC counts = 0. EU = {tag.span_low} {tag.eng_units}.",
                "result": "",
            },
            {
                "step": 4,
                "action": "Perform 5-point check per test table above (0%, 25%, 50%, 75%, 100%). "
                          "Record actual EU reading at each point.",
                "expected": "EU readings within ±0.5% of span of calculated expected values.",
                "result": "",
            },
            {
                "step": 5,
                "action": f"Simulate 20.000 mA (100%). Verify PLC reads {self.project.adc_max_counts()} counts "
                          f"and HMI shows {tag.span_high} {tag.eng_units}.",
                "expected": f"PLC counts = {self.project.adc_max_counts()}. EU = {tag.span_high} {tag.eng_units}.",
                "result": "",
            },
        ]

        if self.tc.include_alarms and tag.alarms:
            steps.append({
                "step": len(steps) + 1,
                "action": "Verify alarm setpoints per alarm table. Simulate value past each setpoint and confirm PLC alarm bit activates.",
                "expected": "All alarm bits activate at configured setpoints. Deadband functions correctly on reset.",
                "result": "",
            })

        steps.append({
            "step": len(steps) + 1,
            "action": "Remove calibrator. Restore loop to normal operating condition.",
            "expected": "Instrument returns to live reading. No faults.",
            "result": "",
        })

        return steps

    def get_doc_metadata(self) -> dict:
        meta = super().get_doc_metadata()
        tag = self.tag
        if tag.sqrt_extraction != SqrtLoc.NONE:
            meta["sqrt_note"] = (
                f"Square root extraction: {tag.sqrt_extraction.value}. "
                f"DP range: {tag.dp_range_low}–{tag.dp_range_high} {tag.dp_units}."
            )
        return meta
