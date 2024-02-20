# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.
from wedge_cli.gui.Controller.home_screen import HomeScreenController
from wedge_cli.gui.Controller.settings_screen import SettingsScreenController
from wedge_cli.gui.Controller.streaming_screen import StreamingScreenController
from wedge_cli.gui.Model.home_screen import HomeScreenModel
from wedge_cli.gui.Model.settings_screen import SettingsScreenModel
from wedge_cli.gui.Model.streaming_screen import StreamingScreenModel

screens = {
    "home screen": {
        "model": HomeScreenModel,
        "controller": HomeScreenController,
    },
    "streaming screen": {
        "model": StreamingScreenModel,
        "controller": StreamingScreenController,
    },
    "settings screen": {
        "model": SettingsScreenModel,
        "controller": SettingsScreenController,
    },
}

start_screen = "home screen"
assert start_screen in screens
