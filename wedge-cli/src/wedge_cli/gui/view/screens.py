# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.
from functools import partial

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
from wedge_cli.gui.view.AIModelScreen.ai_model_screen import AIModelScreenView

screen_dict = {
    "home screen": {
        "model_class": HomeScreenModel,
        "controller_class": HomeScreenController,
    },
    "connection screen": {
        "model_class": ConnectionScreenModel,
        "controller_class": ConnectionScreenController,
    },
    "configuration screen": {
        "model_class": ConfigurationScreenModel,
        "controller_class": ConfigurationScreenController,
    },
    "streaming screen": {
        "model_class": StreamingScreenModel,
        "controller_class": StreamingScreenController,
    },
    "inference screen": {
        "model_class": InferenceScreenModel,
        "controller_class": InferenceScreenController,
    },
    "applications screen": {
        "model_class": ApplicationsScreenModel,
        "controller_class": ApplicationsScreenController,
    },
    "ai model screen": {
        "model_class": AIModelScreenModel,
        "controller_class": partial(AIModelScreenController, view=AIModelScreenView),
    },
}

start_screen = "home screen"
assert start_screen in screen_dict
