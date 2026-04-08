from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .tag import Tag


class PLCPlatform(Enum):
    SIEMENS_S7_1500 = "Siemens S7-1500"
    SIEMENS_S7_300  = "Siemens S7-300/400"
    AB_CONTROLLOGIX = "Allen-Bradley ControlLogix"
    AB_COMPACTLOGIX = "Allen-Bradley CompactLogix"


@dataclass
class Project:
    project_number: str = ""
    project_name: str = ""
    client_name: str = ""
    client_site: str = ""
    si_company: str = ""
    engineer: str = ""
    revision: str = "A"
    revision_date: str = ""
    platform: PLCPlatform = PLCPlatform.SIEMENS_S7_1500
    plc_model: str = ""
    tags: list[Tag] = field(default_factory=list)

    def adc_max_counts(self) -> int:
        if self.platform in (PLCPlatform.SIEMENS_S7_1500, PLCPlatform.SIEMENS_S7_300):
            return 27648
        return 32767  # AB default

    def to_dict(self) -> dict:
        return {
            "project_number": self.project_number,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "client_site": self.client_site,
            "si_company": self.si_company,
            "engineer": self.engineer,
            "revision": self.revision,
            "revision_date": self.revision_date,
            "platform": self.platform.name,
            "plc_model": self.plc_model,
            "tags": [t.to_dict() for t in self.tags],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Project:
        return cls(
            project_number=d.get("project_number", ""),
            project_name=d.get("project_name", ""),
            client_name=d.get("client_name", ""),
            client_site=d.get("client_site", ""),
            si_company=d.get("si_company", ""),
            engineer=d.get("engineer", ""),
            revision=d.get("revision", "A"),
            revision_date=d.get("revision_date", ""),
            platform=PLCPlatform[d.get("platform", "SIEMENS_S7_1500")],
            plc_model=d.get("plc_model", ""),
            tags=[Tag.from_dict(t) for t in d.get("tags", [])],
        )
