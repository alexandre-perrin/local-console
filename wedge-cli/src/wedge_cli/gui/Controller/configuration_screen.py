from pathlib import Path

from wedge_cli.gui.driver import Driver
from wedge_cli.gui.Model.configuration_screen import ConfigurationScreenModel
from wedge_cli.gui.View.ConfigurationScreen.configuration_screen import (
    ConfigurationScreenView,
)


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

    def get_view(self) -> ConfigurationScreenView:
        return self.view

    def update_image_directory(self, path: Path) -> None:
        self.driver.image_directory_config = path
        self.model.image_directory = path

    def update_inferences_directory(self, path: Path) -> None:
        self.driver.inferences_directory_config = path
        self.model.inferences_directory = path
