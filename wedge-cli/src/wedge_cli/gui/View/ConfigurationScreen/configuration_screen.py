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

    def __init__(self, **kargs: Any) -> None:
        super().__init__(**kargs)

        self.manager_open = False
        self.opening_path = Path.cwd()
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager, select_path=self.select_path, search="dirs"
        )
        self.lbl_path_to_be_configured = ""

    def file_manager_open(self, id: str) -> None:
        self.lbl_path_to_be_configured = id
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
        self.ids[self.lbl_path_to_be_configured].text = path

    def exit_manager(self, *args: Any) -> None:
        """Called when the user reaches the root of the directory tree."""
        self.manager_open = False
        self.file_manager.close()
