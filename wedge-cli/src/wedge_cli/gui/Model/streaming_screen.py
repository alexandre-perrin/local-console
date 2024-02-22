from wedge_cli.gui.Model.base_model import BaseScreenModel

ROI = tuple[tuple[int, int], tuple[int, int]]


class StreamingScreenModel(BaseScreenModel):
    """
    The Model for the Streaming screen is composed of two data:
    - The stream status: Active(True) or Inactive(False)
    - The image ROI: a bounding box within the image
    """

    def __init__(self) -> None:
        self._stream_status: bool = False
        self._image_roi: ROI = ((0, 0), (0, 0))

    @property
    def stream_status(self) -> bool:
        return self._stream_status

    @stream_status.setter
    def stream_status(self, value: bool) -> None:
        self._stream_status = value
        self.notify_observers()

    @property
    def image_roi(self) -> ROI:
        return self._image_roi

    @image_roi.setter
    def image_roi(self, value: ROI) -> None:
        self._image_roi = value
        self.notify_observers()
