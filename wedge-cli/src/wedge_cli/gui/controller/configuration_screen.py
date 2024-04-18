from pathlib import Path

from wedge_cli.gui.driver import Driver
from wedge_cli.gui.model.configuration_screen import ConfigurationScreenModel
from wedge_cli.gui.view.ConfigurationScreen.configuration_screen import (
    ConfigurationScreenView,
)
from wedge_cli.utils.flatbuffers import FlatBuffers


class ConfigurationScreenController:
    """
    The `ConfigurationScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ConfigurationScreenModel, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = ConfigurationScreenView(controller=self, model=self.model)
        self.flatbuffers = FlatBuffers()

    def get_view(self) -> ConfigurationScreenView:
        return self.view

    def update_image_directory(self, path: Path) -> None:
        self.driver.set_image_directory(path)
        self.model.image_directory = path

    def update_inferences_directory(self, path: Path) -> None:
        self.driver.set_inference_directory(path)
        self.model.inferences_directory = path

    def update_flatbuffers_schema(self, path: Path) -> None:
        self.model.flatbuffers_schema = path

    def process_schema(self) -> None:
        if self.model.flatbuffers_schema is not None:
            check_file = self.model.flatbuffers_schema.exists()
            if check_file is True:
                result, output = self.flatbuffers.conform_flatbuffer_schema(
                    self.model.flatbuffers_schema
                )
                if result is True:
                    self.driver.flatbuffers_schema = self.model.flatbuffers_schema
                    self.model.flatbuffers_process_result = "Success!"
                else:
                    self.model.flatbuffers_process_result = output
            else:
                self.model.flatbuffers_process_result = "File not exist!"
        else:
            self.model.flatbuffers_process_result = "Please select a schema file."
