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
# This file incorporates material from the KivyMD project, which is licensed
# under the MIT License:
#
#     MIT License
#
#     Copyright (c) 2024 KivyMD contributors
#
#     Permission is hereby granted, free of charge, to any person obtaining a copy
#     of this software and associated documentation files (the "Software"), to deal
#     in the Software without restriction, including without limitation the rights
#     to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#     copies of the Software, and to permit persons to whom the Software is
#     furnished to do so, subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be included in all
#     copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#     IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#     FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#     AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#     LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#     OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#     SOFTWARE.
#
# The following modifications have been made to the original KivyMD code:
#
# - This file started from the project template provided by KivyMD at
#   https://kivymd.readthedocs.io/en/latest/api/kivymd/tools/patterns/create_project/#project-creation
#
# SPDX-License-Identifier: Apache-2.0
from typing import Any
from typing import Optional

from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.snackbar import MDSnackbarButtonContainer
from kivymd.uix.snackbar import MDSnackbarCloseButton
from kivymd.uix.snackbar import MDSnackbarSupportingText
from kivymd.uix.snackbar import MDSnackbarText
from local_console.gui.utils.observer import Observer


class BaseScreenView(MDScreen, Observer):
    """
    A base class that implements a visual representation of the model data.
    The view class must be inherited from this class.
    """

    controller = ObjectProperty()
    """
    Controller object - :class:`~Controller.controller_screen.ClassScreenController`.

    :attr:`controller` is an :class:`~kivy.properties.ObjectProperty`
    and defaults to `None`.
    """

    model = ObjectProperty()
    """
    Model object - :class:`~Model.model_screen.ClassScreenModel`.

    :attr:`model` is an :class:`~kivy.properties.ObjectProperty`
    and defaults to `None`.
    """

    manager_screens = ObjectProperty()
    """
    Screen manager object - :class:`~kivymd.uix.screenmanager.MDScreenManager`.

    :attr:`manager_screens` is an :class:`~kivy.properties.ObjectProperty`
    and defaults to `None`.
    """

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        # Often you need to get access to the application object from the view
        # class. You can do this using this attribute.
        self.app = MDApp.get_running_app()
        # Adding a view class as observer.
        self.model.add_observer(self)

        # Error display widget tracking
        self.error_widget: Optional[MDSnackbar] = None

    def display_error(
        self, text: str, support_text: Optional[str] = None, duration: int = 5
    ) -> None:
        widgets = [
            MDSnackbarText(
                text=text,
                theme_text_color="Error",
            ),
        ]
        if support_text:
            widgets.append(
                MDSnackbarSupportingText(
                    text=support_text,
                    theme_text_color="Secondary",
                )
            )

        self.dismiss_error()
        self.error_widget = MDSnackbar(
            *widgets,
            y=dp(24),
            orientation="horizontal",
            pos_hint={"center_x": 0.5},
            size_hint_x=0.8,
            background_color=self.theme_cls.errorContainerColor,
            duration=duration,
        )
        self.error_widget.add_widget(
            MDSnackbarButtonContainer(
                MDSnackbarCloseButton(
                    icon="close",
                    on_release=self.dismiss_error,
                    theme_icon_color="Custom",
                    icon_color="#2A2B25",
                ),
                pos_hint={"center_y": 0.5},
            )
        )
        self.error_widget.open()

    def dismiss_error(self, *args: Any) -> None:
        if self.error_widget:
            self.error_widget.dismiss()
            self.error_widget = None
