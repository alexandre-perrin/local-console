# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.
from wedge_cli.gui.Controller.home_screen import HomeScreenController
from wedge_cli.gui.Model.home_screen import HomeScreenModel

screens = {
    "home screen": {
        "model": HomeScreenModel,
        "controller": HomeScreenController,
    },
}

start_screen = "home screen"
assert start_screen in screens
