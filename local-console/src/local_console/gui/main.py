# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
The entry point to the application.
#
The application uses the MVC template. Adhering to the principles of clean
architecture means ensuring that your application is easy to test, maintain,
and modernize.
#
You can read more about this template at the links below:
#
https://github.com/HeaTTheatR/LoginAppMVC
https://en.wikipedia.org/wiki/Model–view–controller
"""
import logging
from typing import Any

from kivy.base import ExceptionHandler
from kivy.base import ExceptionManager
from kivy.properties import BooleanProperty
from kivy.properties import StringProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from local_console.gui.config import configure
from local_console.gui.driver import Driver
from local_console.gui.view.screens import screen_dict
from local_console.gui.view.screens import start_screen

logger = logging.getLogger(__name__)


class LocalConsoleGUIAPP(MDApp):
    nursery = None
    driver = None

    # Proxy objects leveraged for using Kivy's event dispatching
    is_ready = BooleanProperty(False)
    is_streaming = BooleanProperty(False)
    image_dir_path = StringProperty("")
    inference_dir_path = StringProperty("")

    async def app_main(self) -> None:
        self.driver = Driver(self)
        await self.driver.main()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.load_all_kv_files(self.directory)
        self.manager_screens = MDScreenManager()
        self.views: dict[str, type[MDScreen]] = {}
        configure()

    def build(self) -> MDScreenManager:
        self.title = "Local Console"
        self.generate_application_screens()
        return self.manager_screens

    def generate_application_screens(self) -> None:
        """
        Creating and adding screens to the screen manager.
        You should not change this cycle unnecessarily. It is self-sufficient.

        If you need to add any screen, open the `View.screens.py` module and
        see how new screens are added according to the given application
        architecture.
        """

        for name, entry in screen_dict.items():
            # TODO:FIXME: as a consequence of decouple viewer and controller
            model = entry["model_class"]()  # type: ignore
            controller = entry["controller_class"](model, self.driver)  # type: ignore
            view = controller.get_view()
            view.manager_screens = self.manager_screens
            view.name = name

            view.theme_cls.theme_style = "Light"
            view.theme_cls.primary_palette = (
                "Green"  # Pick one from kivymd.theming.ThemeManager.primary_palette
            )

            self.manager_screens.add_widget(view)
            self.views[name] = view

        self.manager_screens.current = start_screen


class GUIExceptionHandler(ExceptionHandler):
    def handle_exception(self, inst: BaseException) -> Any:
        if isinstance(inst, KeyboardInterrupt):
            # The user requested cancellation, so this is handled.
            return ExceptionManager.RAISE

        logger.exception("Uncaught Kivy exception ocurred:", exc_info=inst)
        cause = inst.__traceback__
        assert cause  # appease mypy
        while cause.tb_next:
            cause = cause.tb_next
        """
        TODO Decide whether to return .RAISE or .PASS depending
             on the 'cause'. If .PASS, maybe we can show it on
             the GUI itself!
        """
        return ExceptionManager.RAISE


ExceptionManager.add_handler(GUIExceptionHandler())
