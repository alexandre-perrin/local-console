# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.
from wedge_cli.gui.Controller.applications_screen import ApplicationsScreenController
from wedge_cli.gui.Controller.configuration_screen import ConfigurationScreenController
from wedge_cli.gui.Controller.connection_screen import ConnectionScreenController
from wedge_cli.gui.Controller.home_screen import HomeScreenController
from wedge_cli.gui.Controller.inference_screen import InferenceScreenController
from wedge_cli.gui.Controller.streaming_screen import StreamingScreenController
from wedge_cli.gui.Model.applications_screen import ApplicationsScreenModel
from wedge_cli.gui.Model.configuration_screen import ConfigurationScreenModel
from wedge_cli.gui.Model.connection_screen import ConnectionScreenModel
from wedge_cli.gui.Model.home_screen import HomeScreenModel
from wedge_cli.gui.Model.inference_screen import InferenceScreenModel
from wedge_cli.gui.Model.streaming_screen import StreamingScreenModel

screens = {
    "home screen": {
        "model": HomeScreenModel,
        "controller": HomeScreenController,
    },
    "connection screen": {
        "model": ConnectionScreenModel,
        "controller": ConnectionScreenController,
    },
    "configuration screen": {
        "model": ConfigurationScreenModel,
        "controller": ConfigurationScreenController,
    },
    "streaming screen": {
        "model": StreamingScreenModel,
        "controller": StreamingScreenController,
    },
    "inference screen": {
        "model": InferenceScreenModel,
        "controller": InferenceScreenController,
    },
    "applications screen": {
        "model": ApplicationsScreenModel,
        "controller": ApplicationsScreenController,
    },
}

start_screen = "home screen"
assert start_screen in screens
