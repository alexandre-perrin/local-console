from wedge_cli.core.camera import StreamStatus
from wedge_cli.gui.Model.base_model import BaseScreenModel


class InferenceScreenModel(BaseScreenModel):
    """
    The Model for the Inference screen is composed of the data:
    - The stream status: Active(True) or Inactive(False)
    """

    def __init__(self) -> None:
        self._stream_status = StreamStatus.Inactive

    @property
    def stream_status(self) -> StreamStatus:
        return self._stream_status

    @stream_status.setter
    def stream_status(self, value: StreamStatus) -> None:
        self._stream_status = value
        self.notify_observers()
