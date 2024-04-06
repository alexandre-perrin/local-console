# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.
from wedge_cli.gui.controller.ai_model_screen import AIModelScreenController
from wedge_cli.gui.controller.applications_screen import ApplicationsScreenController
from wedge_cli.gui.controller.configuration_screen import ConfigurationScreenController
from wedge_cli.gui.controller.connection_screen import ConnectionScreenController
from wedge_cli.gui.controller.home_screen import HomeScreenController
from wedge_cli.gui.controller.inference_screen import InferenceScreenController
from wedge_cli.gui.controller.streaming_screen import StreamingScreenController
from wedge_cli.gui.model.ai_model_screen import AIModelScreenModel
from wedge_cli.gui.model.applications_screen import ApplicationsScreenModel
from wedge_cli.gui.model.configuration_screen import ConfigurationScreenModel
from wedge_cli.gui.model.connection_screen import ConnectionScreenModel
from wedge_cli.gui.model.home_screen import HomeScreenModel
from wedge_cli.gui.model.inference_screen import InferenceScreenModel
from wedge_cli.gui.model.streaming_screen import StreamingScreenModel

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
    "ai model screen": {
        "model": AIModelScreenModel,
        "controller": AIModelScreenController,
    },
}

start_screen = "home screen"
assert start_screen in screens
