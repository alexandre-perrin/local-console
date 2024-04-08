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
from wedge_cli.gui.view.base_screen import BaseScreenView
from wedge_cli.utils.validation import validate_app_file

logger = logging.getLogger(__name__)


class ApplicationsScreenView(BaseScreenView):
    deploy_status = StringProperty("")

    def model_is_changed(self) -> None:
        reconcile_status = self.model.deploy_status.get("reconcileStatus")
        if reconcile_status:
            self.ids.lbl_deployment_status.text = reconcile_status
        self.ids.txt_deployment_data.text = json.dumps(
            self.model.deploy_status, indent=4
        )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.app.bind(is_ready=self.app_state_refresh)

        self.manager_open = False
        self.opening_path = Path.cwd()
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
            selector="file",
        )

    def file_manager_open(self) -> None:
        self.file_manager.show(str(self.opening_path))
        self.manager_open = True

    def select_path(self, path: str) -> None:
        """
        It will be called when the user clicks on the file name
        or the catalog selection button.

        :param path: path to the selected directory or file;
        """
        self.exit_manager()
        self.opening_path = Path(path).parent
        if validate_app_file(Path(path)):
            self.ids.lbl_app_path.text = path
            self.ids.btn_deploy_file.disabled = not self.app.is_ready
        else:
            self.ids.btn_deploy_file.disabled = True
            MDSnackbar(
                MDSnackbarSupportingText(
                    text="Invalid AOT-compiled module file",
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
        self.ids.btn_deploy_file.disabled = not self.app.is_ready
