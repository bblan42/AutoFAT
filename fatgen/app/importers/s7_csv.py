"""
Siemens S7-1500 TIA Portal CSV importer.

Supports two export formats:
  1. Standard tag table export: Name, Path, Data Type, Logical Address, Comment
  2. I/O device view export (adds rack/slot/channel columns)
"""
from __future__ import annotations
import re
import csv
import io
from collections import defaultdict
from ..models.tag import Tag, IOType, SignalType, SqrtLoc, AlarmSetpoint
from .base import BaseImporter

# Address patterns
_AI  = re.compile(r'%IW(\d+)')
_AO  = re.compile(r'%QW(\d+)')
_DI  = re.compile(r'%I(\d+)\.(\d+)')
_DO  = re.compile(r'%Q(\d+)\.(\d+)')
_MEM = re.compile(r'%M(\d+)\.(\d+)')
_DB  = re.compile(r'%DB(\d+)\.DBX(\d+)\.(\d+)')

# Suffix heuristics for auto-grouping
_ALARM_SUFFIXES = re.compile(r'_(HH|H|L|LL)$', re.IGNORECASE)
_EU_SUFFIXES    = re.compile(r'_(EU|PV|SP|CV)$', re.IGNORECASE)
_MOTOR_START    = re.compile(r'_START$', re.IGNORECASE)
_MOTOR_RUN      = re.compile(r'_RUN$', re.IGNORECASE)
_MOTOR_FAULT    = re.compile(r'_(FAULT|FLT)$', re.IGNORECASE)
_MOTOR_STOP     = re.compile(r'_STOP$', re.IGNORECASE)


def _parse_address(addr: str) -> tuple[IOType, int, int, int]:
    """Return (io_type, rack, byte_offset, bit). Rack always 0 for S7 tag table."""
    addr = addr.strip()
    m = _AI.match(addr)
    if m:
        return IOType.AI, 0, int(m.group(1)), 0
    m = _AO.match(addr)
    if m:
        return IOType.AO, 0, int(m.group(1)), 0
    m = _DI.match(addr)
    if m:
        return IOType.DI, 0, int(m.group(1)), int(m.group(2))
    m = _DO.match(addr)
    if m:
        return IOType.DO, 0, int(m.group(1)), int(m.group(2))
    m = _MEM.match(addr)
    if m:
        return IOType.MEM, 0, int(m.group(1)), int(m.group(2))
    m = _DB.match(addr)
    if m:
        return IOType.DB, 0, int(m.group(2)), int(m.group(3))
    return IOType.UNKNOWN, 0, 0, 0


def _base_name(name: str) -> str:
    """Strip known suffixes to find the base instrument tag name."""
    for pattern in (_ALARM_SUFFIXES, _EU_SUFFIXES, _MOTOR_RUN, _MOTOR_FAULT,
                    _MOTOR_STOP, _MOTOR_START):
        stripped = pattern.sub('', name)
        if stripped != name:
            return stripped
    return name


class S7CSVImporter(BaseImporter):

    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def parse(self, filepath: str) -> list[Tag]:
        with open(filepath, newline='', encoding='utf-8-sig') as f:
            return self.parse_text(f.read())

    def parse_text(self, text: str) -> list[Tag]:
        """Parse CSV text (useful for web upload where we have a string)."""
        reader = csv.DictReader(io.StringIO(text))
        # Normalise header names — TIA Portal sometimes adds BOM or extra spaces
        rows = []
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()})

        if not rows:
            return []

        # Detect which column names are present
        headers = list(rows[0].keys())
        name_col    = _find_col(headers, ["Name", "Tag name"])
        addr_col    = _find_col(headers, ["Logical Address", "Address", "Logical address"])
        comment_col = _find_col(headers, ["Comment", "Description"])
        dtype_col   = _find_col(headers, ["Data Type", "DataType", "Data type"])

        raw_tags: list[Tag] = []
        for row in rows:
            name = row.get(name_col, "").strip()
            if not name or name.startswith("//"):
                continue
            addr    = row.get(addr_col, "").strip()
            comment = row.get(comment_col, "").strip()

            io_type, rack, byte_off, bit = _parse_address(addr)

            tag = Tag(
                name=name,
                description=comment,
                io_type=io_type,
                address=addr,
                rack=rack,
                slot=0,
                channel=byte_off,
                signal_type=SignalType.mA_4_20 if io_type in (IOType.AI, IOType.AO) else SignalType.DISCRETE,
            )
            raw_tags.append(tag)

        return self._post_process(raw_tags)

    def _post_process(self, tags: list[Tag]) -> list[Tag]:
        """
        Auto-group related tags:
        - Mark _HH/_H/_L/_LL tags as alarm bits on the parent AI tag
        - Skip _EU/_PV linked tags (they're derived values, not test subjects)
        - Group motor tag sets
        """
        tag_map = {t.name: t for t in tags}
        skip = set()
        alarm_map: dict[str, list[AlarmSetpoint]] = defaultdict(list)

        for tag in tags:
            # Alarm bit grouping
            m = _ALARM_SUFFIXES.search(tag.name)
            if m and tag.io_type in (IOType.MEM, IOType.DB, IOType.DI):
                level = m.group(1).upper()
                base = _base_name(tag.name)
                if base in tag_map:
                    alarm_map[base].append(AlarmSetpoint(
                        level=level,
                        setpoint=0.0,
                        deadband=0.0,
                        plc_bit=tag.address,
                    ))
                    skip.add(tag.name)
                continue

            # EU/PV/SP linked value — mark to skip
            if _EU_SUFFIXES.search(tag.name):
                skip.add(tag.name)

        # Apply gathered alarms to parent tags
        for base_name, alarms in alarm_map.items():
            if base_name in tag_map:
                alarms.sort(key=lambda a: ["HH", "H", "L", "LL"].index(a.level)
                            if a.level in ["HH", "H", "L", "LL"] else 99)
                tag_map[base_name].alarms = alarms

        return [t for t in tags if t.name not in skip]


def _find_col(headers: list[str], candidates: list[str]) -> str:
    """Return the first matching header name (case-insensitive)."""
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return candidates[0]  # fallback — will produce empty values gracefully
