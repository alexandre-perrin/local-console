from wedge_cli.gui.driver import Driver
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

    def __init__(self, model: ConfigurationScreenView, driver: Driver) -> None:
        self.model = model
        self.driver = driver
        self.view = ConfigurationScreenView(controller=self, model=self.model)

    def get_view(self) -> ConfigurationScreenView:
        return self.view
