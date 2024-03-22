from pathlib import Path

from trio import Event
from wedge_cli.gui.Model.base_model import BaseScreenModel


class AIModelScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.settings_screen.AIModelScreen.AIModelScreenView` class.
    """

    def __init__(self) -> None:
        self._ota_status: dict[str, str] = {}

        # These two variables enable signaling that the OTA
        # status has changed from a previous report
        self._ota_event = Event()
        self._ota_status_previous: dict[str, str] = {}

        self._model_file = Path()
        self._model_file_valid = False

    @property
    def ota_status(self) -> dict[str, str]:
        return self._ota_status

    @ota_status.setter
    def ota_status(self, value: dict[str, str]) -> None:
        self._ota_status = value

        # detect content change
        if self._ota_status_previous != value:
            self._ota_status_previous = value
            self._ota_event.set()
            self.notify_observers()

    async def ota_event(self) -> None:
        self._ota_event = Event()
        await self._ota_event.wait()

    @property
    def model_file(self) -> Path:
        return self._model_file

    @model_file.setter
    def model_file(self, value: Path) -> None:
        self._model_file = value
        # TODO perform actual validation
        self._model_file_valid = True

        self.notify_observers()

    @property
    def model_file_valid(self) -> bool:
        return self._model_file_valid
