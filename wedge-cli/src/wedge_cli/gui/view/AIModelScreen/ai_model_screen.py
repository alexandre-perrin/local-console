import json
import logging
from pathlib import Path
from typing import Any

from kivy.metrics import dp
from kivy.properties import StringProperty
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.snackbar import MDSnackbarButtonContainer
from kivymd.uix.snackbar import MDSnackbarCloseButton
from kivymd.uix.snackbar import MDSnackbarSupportingText
from wedge_cli.gui.utils.sync_async import run_on_ui_thread
from wedge_cli.gui.view.base_screen import BaseScreenView

logger = logging.getLogger(__name__)


class AIModelScreenView(BaseScreenView):
    ota_status = StringProperty("")

    def model_is_changed(self) -> None:
        self.ids.txt_ota_data.text = json.dumps(self.model.ota_status, indent=4)

        update_status = self.model.ota_status.get("UpdateStatus")
        if update_status:
            self.ids.lbl_ota_status.text = update_status

        if self.model.model_file.is_file():
            self.ids.lbl_app_path.text = str(self.model.model_file)

        can_deploy = (
            self.app.is_ready
            and self.model.model_file_valid
            and update_status in ("Done", "Failed")
        )
        self.ids.btn_ota_file.disabled = not can_deploy

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.app.bind(is_ready=self.app_state_refresh)

        self.manager_open = False
        self.opening_path = Path.cwd()
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager, select_path=self.select_path
        )

    def file_manager_open(self) -> None:
        self.file_manager.show(str(self.opening_path))
        self.manager_open = True

    def select_path(self, path_str: str) -> None:
        """
        It will be called when the user clicks on the file name
        or the catalog selection button.

        :param path: path to the selected directory or file;
        """
        self.exit_manager()
        path = Path(path_str)
        self.opening_path = path.parent
        self.model.model_file = path

        if not self.model.model_file_valid:
            MDSnackbar(
                MDSnackbarSupportingText(
                    text="Invalid AI Model file header!",
                ),
                MDSnackbarButtonContainer(
                    MDSnackbarCloseButton(
                        icon="close",
                    ),
                    pos_hint={"center_y": 0.5},
                ),
                y=dp(24),
                orientation="horizontal",
                pos_hint={"center_x": 0.5},
                size_hint_x=0.5,
            ).open()

    def exit_manager(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.manager_open = False
        self.file_manager.close()

    def app_state_refresh(self, app: MDApp, value: bool) -> None:
        """
        Makes the deploy button react to the camera readiness state.
        """
        self.ids.btn_ota_file.disabled = not self.app.is_ready

    @run_on_ui_thread
    def notify_deploy_timeout(self) -> None:
        MDSnackbar(
            MDSnackbarSupportingText(
                text="Model deployment timed out!",
            ),
            MDSnackbarButtonContainer(
                MDSnackbarCloseButton(
                    icon="close",
                ),
                pos_hint={"center_y": 0.5},
            ),
            y=dp(24),
            orientation="horizontal",
            pos_hint={"center_x": 0.5},
            size_hint_min_x=0.5,
            size_hint_max_x=0.9,
        ).open()
