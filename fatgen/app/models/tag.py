from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IOType(Enum):
    AI = "Analog Input"
    AO = "Analog Output"
    DI = "Discrete Input"
    DO = "Discrete Output"
    MEM = "Memory"
    DB = "Data Block"
    UNKNOWN = "Unknown"


class SignalType(Enum):
    mA_4_20 = "4-20 mA"
    V_1_5 = "1-5 VDC"
    V_0_10 = "0-10 VDC"
    DISCRETE = "Discrete"
    NONE = "N/A"


class SqrtLoc(Enum):
    CONTROLLER = "Controller (PLC)"
    TRANSMITTER = "Transmitter (HART)"
    NONE = "Not Applicable"


@dataclass
class AlarmSetpoint:
    level: str          # "HH", "H", "L", "LL"
    setpoint: float
    deadband: float = 0.0
    plc_bit: str = ""   # "%M100.3"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "setpoint": self.setpoint,
            "deadband": self.deadband,
            "plc_bit": self.plc_bit,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AlarmSetpoint:
        return cls(
            level=d["level"],
            setpoint=d["setpoint"],
            deadband=d.get("deadband", 0.0),
            plc_bit=d.get("plc_bit", ""),
        )


@dataclass
class Tag:
    name: str
    description: str = ""
    io_type: IOType = IOType.UNKNOWN
    address: str = ""
    rack: int = 0
    slot: int = 0
    channel: int = 0
    instrument_model: str = ""
    span_low: float = 0.0
    span_high: float = 100.0
    eng_units: str = ""
    signal_type: SignalType = SignalType.mA_4_20
    adc_resolution: int = 16
    sqrt_extraction: SqrtLoc = SqrtLoc.NONE
    dp_range_low: float = 0.0
    dp_range_high: float = 100.0
    dp_units: str = "in H2O"
    alarms: list[AlarmSetpoint] = field(default_factory=list)
    plc_alarm_bits: dict = field(default_factory=dict)
    interlock_tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "io_type": self.io_type.name,
            "address": self.address,
            "rack": self.rack,
            "slot": self.slot,
            "channel": self.channel,
            "instrument_model": self.instrument_model,
            "span_low": self.span_low,
            "span_high": self.span_high,
            "eng_units": self.eng_units,
            "signal_type": self.signal_type.name,
            "adc_resolution": self.adc_resolution,
            "sqrt_extraction": self.sqrt_extraction.name,
            "dp_range_low": self.dp_range_low,
            "dp_range_high": self.dp_range_high,
            "dp_units": self.dp_units,
            "alarms": [a.to_dict() for a in self.alarms],
            "plc_alarm_bits": self.plc_alarm_bits,
            "interlock_tags": self.interlock_tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Tag:
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            io_type=IOType[d.get("io_type", "UNKNOWN")],
            address=d.get("address", ""),
            rack=d.get("rack", 0),
            slot=d.get("slot", 0),
            channel=d.get("channel", 0),
            instrument_model=d.get("instrument_model", ""),
            span_low=d.get("span_low", 0.0),
            span_high=d.get("span_high", 100.0),
            eng_units=d.get("eng_units", ""),
            signal_type=SignalType[d.get("signal_type", "mA_4_20")],
            adc_resolution=d.get("adc_resolution", 16),
            sqrt_extraction=SqrtLoc[d.get("sqrt_extraction", "NONE")],
            dp_range_low=d.get("dp_range_low", 0.0),
            dp_range_high=d.get("dp_range_high", 100.0),
            dp_units=d.get("dp_units", "in H2O"),
            alarms=[AlarmSetpoint.from_dict(a) for a in d.get("alarms", [])],
            plc_alarm_bits=d.get("plc_alarm_bits", {}),
            interlock_tags=d.get("interlock_tags", []),
            notes=d.get("notes", ""),
        )
