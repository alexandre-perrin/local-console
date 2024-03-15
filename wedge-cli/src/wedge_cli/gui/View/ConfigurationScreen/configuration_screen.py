from pathlib import Path
from typing import Any

from kivymd.uix.filemanager import MDFileManager
from wedge_cli.gui.View.base_screen import BaseScreenView


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
        if self.model.flatbuffers_directory is not None:
            self.ids.lbl_scheme_path.text = str(self.model.flatbuffers_directory)

    def __init__(self, **kargs: Any) -> None:
        super().__init__(**kargs)

        self.manager_open_image = False
        self.manager_open_inferences = False
        self.manager_open_flatbuffers = False

        self.file_manager_image = MDFileManager(
            exit_manager=self.exit_manager_image, select_path=self.select_path_image, search="dirs"
        )
        self.file_manager_inferences = MDFileManager(
            exit_manager=self.exit_manager_inferences, select_path=self.select_path_inferences, search="dirs"
        )
        self.file_manager_flatbuffers = MDFileManager(
            exit_manager=self.exit_manager_flatbuffers, select_path=self.select_path_flatbuffers, search="dirs"
        )

        self.opening_path = Path.cwd()

    def file_manager_open_image(self) -> None:
        self.file_manager_image.show(str(self.opening_path))
        self.manager_open_image = True

    def file_manager_open_inferences(self) -> None:
        self.file_manager_inferences.show(str(self.opening_path))
        self.manager_open_inferences = True

    def file_manager_open_flatbuffers(self) -> None:
        self.file_manager_flatbuffers.show(str(self.opening_path))
        self.manager_open_flatbuffers = True

    def select_path_image(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_image()
        self.opening_path = Path(path).parent
        self.controller.update_image_directory(Path(path))

    def select_path_inferences(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_inferences()
        self.opening_path = Path(path).parent
        self.controller.update_inferences_directory(Path(path))

    def select_path_flatbuffers(self, path: str) -> None:
        """
        It will be called when the user selects the directory.
        :param path: path to the selected directory;
        """
        self.exit_manager_flatbuffers()
        self.opening_path = Path(path).parent
        self.ids.lbl_scheme_path.text = path

    def exit_manager_image(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.manager_open_image = False
        self.file_manager_image.close()

    def exit_manager_inferences(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.manager_open_inferences = False
        self.file_manager_inferences.close()

    def exit_manager_flatbuffers(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.manager_open_flatbuffers = False
        self.file_manager_flatbuffers.close()
