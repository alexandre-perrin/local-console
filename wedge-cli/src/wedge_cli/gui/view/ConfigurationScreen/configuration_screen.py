from pathlib import Path
from typing import Any

from kivy.metrics import dp
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.snackbar import MDSnackbarButtonContainer
from kivymd.uix.snackbar import MDSnackbarCloseButton
from kivymd.uix.snackbar import MDSnackbarSupportingText
from wedge_cli.gui.view.base_screen import BaseScreenView
from wedge_cli.gui.view.common.components import FileManager


class ConfigurationScreenView(BaseScreenView):
    def model_is_changed(self) -> None:
        """
        Called whenever any change has occurred in the data model.
        The view in this method tracks these changes and updates the UI
        according to these changes.
        """
        if self.model.image_directory is not None:
            self.ids.lbl_image_path.text = str(self.model.image_directory)
        if self.model.inferences_directory is not None:
            self.ids.lbl_inference_path.text = str(self.model.inferences_directory)
        if self.model.flatbuffers_schema is not None:
            self.ids.lbl_schema_path.text = str(self.model.flatbuffers_schema)
        if self.model.flatbuffers_process_result is not None:
            self.show_flatbuffers_process_result(self.model.flatbuffers_process_result)
            self.model.flatbuffers_process_result = None

    def __init__(self, **kargs: Any) -> None:
        super().__init__(**kargs)

        self.file_manager_image = FileManager(
            exit_manager=self.exit_manager_image,
            select_path=self.select_path_image,
            search="dirs",
        )
        self.file_manager_inferences = FileManager(
            exit_manager=self.exit_manager_inferences,
            select_path=self.select_path_inferences,
            search="dirs",
        )
        self.file_manager_flatbuffers = FileManager(
            exit_manager=self.exit_manager_flatbuffers,
            select_path=self.select_path_flatbuffers,
            ext=[".fbs"],
        )

    def select_path_image(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_image()
        self.file_manager_image.refresh_opening_path()
        self.controller.update_image_directory(Path(path))

    def select_path_inferences(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_inferences()
        self.file_manager_inferences.refresh_opening_path()
        self.controller.update_inferences_directory(Path(path))

    def select_path_flatbuffers(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_flatbuffers()
        self.file_manager_flatbuffers.refresh_opening_path()
        self.controller.update_flatbuffers_schema(Path(path))

    def exit_manager_image(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.file_manager_image.close()

    def exit_manager_inferences(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.file_manager_inferences.close()

    def exit_manager_flatbuffers(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.file_manager_flatbuffers.close()

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
