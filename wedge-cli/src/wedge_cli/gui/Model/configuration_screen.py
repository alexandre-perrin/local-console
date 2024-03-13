from pathlib import Path

from wedge_cli.gui.Model.base_model import BaseScreenModel


class ConfigurationScreenModel(BaseScreenModel):
    """
    The Model for the Configuration screen.
    """

    def __init__(self) -> None:
        self._image_directory: Path
        self._inferences_directory: Path
        self._flatbuffers_directory: Path

    @property
    def image_directory(self) -> Path:
        return self._image_directory

    @image_directory.setter
    def image_directory(self, value: Path) -> None:
        self._image_directory = value
        self.notify_observers()

    @property
    def inferences_directory(self) -> Path:
        return self._inferences_directory

    @inferences_directory.setter
    def inferences_directory(self, value: Path) -> None:
        self._inferences_directory = value
        self.notify_observers()

    @property
    def flatbuffers_directory(self) -> Path:
        return self._flatbuffers_directory

    @flatbuffers_directory.setter
    def flatbuffers_directory(self, value: Path) -> None:
        self._flatbuffers_directory = value
        self.notify_observers()
