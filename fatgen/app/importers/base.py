from abc import ABC, abstractmethod
from ..models.tag import Tag


class BaseImporter(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> list[Tag]:
        """Parse the source file and return a list of Tag objects."""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        pass
