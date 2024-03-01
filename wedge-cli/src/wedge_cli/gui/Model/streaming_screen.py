from wedge_cli.gui.camera import StreamStatus
from wedge_cli.gui.Model.base_model import BaseScreenModel
from wedge_cli.gui.Utility.axis_mapping import DEFAULT_ROI
from wedge_cli.gui.Utility.axis_mapping import UnitROI


class StreamingScreenModel(BaseScreenModel):
    """
    The Model for the Streaming screen is composed of two data:
    - The stream status: Active(True) or Inactive(False)
    - The image ROI: a bounding box within the image
    """

    def __init__(self) -> None:
        self._stream_status = StreamStatus.Inactive
        self._image_roi: UnitROI = DEFAULT_ROI

    @property
    def stream_status(self) -> StreamStatus:
        return self._stream_status

    @stream_status.setter
    def stream_status(self, value: StreamStatus) -> None:
        self._stream_status = value
        self.notify_observers()

    @property
    def image_roi(self) -> UnitROI:
        return self._image_roi

    @image_roi.setter
    def image_roi(self, value: UnitROI) -> None:
        self._image_roi = value
        self.notify_observers()

    @property
    def has_default_roi(self) -> bool:
        return self.image_roi == DEFAULT_ROI
