from pathlib import Path

from wedge_cli.core.camera import StreamStatus
from wedge_cli.gui.Model.base_model import BaseScreenModel


class InferenceScreenModel(BaseScreenModel):
    """
    The Model for the Inference screen is composed of the data:
    - The stream status: Active(True) or Inactive(False)
    - The image directory: path of the image directory
    - The inferences directory: path of the inferences directory
    """

    def __init__(self) -> None:
        self._stream_status = StreamStatus.Disabled
        self._image_directory = None
        self._inferences_directory = None

    @property
    def stream_status(self) -> StreamStatus:
        return self._stream_status

    @stream_status.setter
    def stream_status(self, value: StreamStatus) -> None:
        self._stream_status = value
        self.notify_observers()

    @property
    def image_directory(self) -> None:
        return self._image_directory

    @image_directory.setter
    def image_directory(self, value: Path) -> None:
        self._image_directory = value
        self.notify_observers()

    @property
    def inferences_directory(self) -> None:
        return self._inferences_directory

    @inferences_directory.setter
    def inferences_directory(self, value: Path) -> None:
        self._inferences_directory = value
        self.notify_observers()
