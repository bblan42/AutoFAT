from abc import ABC, abstractmethod
from ..models.tag import Tag
from ..models.test_config import TestCase
from ..models.project import Project


class TestTemplate(ABC):
    def __init__(self, test_case: TestCase, tag: Tag, project: Project):
        self.tc = test_case
        self.tag = tag
        self.project = project

    @abstractmethod
    def get_test_points(self) -> list[dict]:
        """Return list of test point row dicts for the main test table."""
        pass

    @abstractmethod
    def get_steps(self) -> list[dict]:
        """Return ordered list of {step, action, expected, result} dicts."""
        pass

    def get_doc_metadata(self) -> dict:
        """Returns header/info-table fields for the rendered document."""
        return {
            "doc_number": self.tc.doc_number,
            "test_type": self.tc.test_type.value,
            "tag_name": self.tag.name,
            "description": self.tag.description,
            "address": self.tag.address,
            "instrument_model": self.tag.instrument_model,
            "span": f"{self.tag.span_low} – {self.tag.span_high} {self.tag.eng_units}",
            "signal_type": self.tag.signal_type.value,
            "client": self.project.client_name,
            "client_site": self.project.client_site,
            "project_number": self.project.project_number,
            "project_name": self.project.project_name,
            "si_company": self.project.si_company,
            "engineer": self.project.engineer,
            "revision": self.project.revision,
            "revision_date": self.project.revision_date,
            "plc_platform": self.project.platform.value,
            "plc_model": self.project.plc_model,
            "notes": self.tc.notes,
            "witness_blocks": self.tc.witness_blocks,
        }
