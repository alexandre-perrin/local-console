from pathlib import Path
from typing import Any

from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.snackbar import MDSnackbarButtonContainer
from kivymd.uix.snackbar import MDSnackbarCloseButton
from kivymd.uix.snackbar import MDSnackbarSupportingText
from wedge_cli.gui.view.base_screen import BaseScreenView
from wedge_cli.gui.view.common.components import (
    PathSelectorCombo,
)  # nopycln: import # Required by the screen's KV spec file


class ConfigurationScreenView(BaseScreenView):
    image_dir_picker = ObjectProperty()
    inference_dir_picker = ObjectProperty()

    def model_is_changed(self) -> None:
        """
        Called whenever any change has occurred in the data model.
        The view in this method tracks these changes and updates the UI
        according to these changes.
        """
        if self.model.image_directory is not None:
            self.image_dir_picker.accept_path(str(self.model.image_directory))
        if self.model.inferences_directory is not None:
            self.inference_dir_picker.accept_path(str(self.model.inferences_directory))
        if self.model.flatbuffers_schema is not None:
            self.ids.schema_pick.accept_path(str(self.model.flatbuffers_schema))
        if self.model.flatbuffers_process_result is not None:
            self.show_flatbuffers_process_result(self.model.flatbuffers_process_result)
            self.model.flatbuffers_process_result = None

    def __init__(self, **kargs: Any) -> None:
        super().__init__(**kargs)

        self.image_dir_picker.file_manager.select_path = self.select_path_image
        self.image_dir_picker.file_manager.search = "dirs"

        self.inference_dir_picker.file_manager.select_path = self.select_path_inferences
        self.inference_dir_picker.file_manager.search = "dirs"

        self.ids.schema_pick.file_manager.select_path = self.select_path_flatbuffers
        self.ids.schema_pick.file_manager.ext = [".fbs"]

    def select_path_image(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.image_dir_picker.file_manager.exit_manager()
        self.controller.update_image_directory(Path(path))

    def select_path_inferences(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.inference_dir_picker.file_manager.exit_manager()
        self.controller.update_inferences_directory(Path(path))

    def select_path_flatbuffers(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.ids.schema_pick.file_manager.exit_manager()
        self.controller.update_flatbuffers_schema(Path(path))

    def show_flatbuffers_process_result(self, result: str) -> None:
        MDSnackbar(
            MDSnackbarSupportingText(text=result),
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
            duration=5,
        ).open()
