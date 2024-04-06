from pathlib import Path
from typing import Optional

from wedge_cli.gui.model.base_model import BaseScreenModel


class ConfigurationScreenModel(BaseScreenModel):
    """
    The Model for the Configuration screen.
    """

    def __init__(self) -> None:
        self._image_directory: Optional[Path] = None
        self._inferences_directory: Optional[Path] = None
        self._flatbuffers_schema: Optional[Path] = None
        self._flatbuffers_process_result: Optional[str] = None
        self._flatbuffers_schema_status: bool = False

    @property
    def image_directory(self) -> Optional[Path]:
        return self._image_directory

    @image_directory.setter
    def image_directory(self, value: Optional[Path]) -> None:
        self._image_directory = value
        self.notify_observers()

    @property
    def inferences_directory(self) -> Optional[Path]:
        return self._inferences_directory

    @inferences_directory.setter
    def inferences_directory(self, value: Optional[Path]) -> None:
        self._inferences_directory = value
        self.notify_observers()

    @property
    def flatbuffers_schema(self) -> Optional[Path]:
        return self._flatbuffers_schema

    @flatbuffers_schema.setter
    def flatbuffers_schema(self, value: Optional[Path]) -> None:
        self._flatbuffers_schema = value
        self.notify_observers()

    @property
    def flatbuffers_process_result(self) -> Optional[str]:
        return self._flatbuffers_process_result

    @flatbuffers_process_result.setter
    def flatbuffers_process_result(self, value: Optional[str]) -> None:
        self._flatbuffers_process_result = value
        self.notify_observers()

    @property
    def flatbuffers_schema_status(self) -> bool:
        return self._flatbuffers_schema_status

    @flatbuffers_schema_status.setter
    def flatbuffers_schema_status(self, value: bool) -> None:
        self._flatbuffers_schema_status = value
        self.notify_observers()
