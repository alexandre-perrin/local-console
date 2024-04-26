from local_console.gui.driver import Driver
from local_console.gui.model.base_model import BaseScreenModel
from local_console.gui.view.HomeScreen.home_screen import HomeScreenView


class HomeScreenController:
    """
    The `HomeScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: BaseScreenModel, driver: Driver):
        self.model = model  # Model.home_screen.HomeScreenModel
        self.driver = driver
        self.view = HomeScreenView(controller=self, model=self.model)

    def get_view(self) -> HomeScreenView:
        return self.view
