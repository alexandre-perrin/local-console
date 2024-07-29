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
import json
import logging
from pathlib import Path
from typing import Any
from typing import Optional

from kivy.properties import BooleanProperty
from kivy.uix.image import Image
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon
from kivymd.uix.label import MDLabel
from local_console.core.commands.deploy import DeployStage
from local_console.gui.config import resource_path
from local_console.gui.view.base_screen import BaseScreenView
from local_console.gui.view.common.components import (
    GUITooltip,
)
from local_console.utils.validation import validate_app_file

logger = logging.getLogger(__name__)


class StatusLabel(GUITooltip, MDLabel):
    """
    Endows a Label with a given tooltip. See the associated KV file.
    """


class ApplicationsScreenView(BaseScreenView):

    app_file_valid = BooleanProperty(False)

    def model_is_changed(self) -> None:
        self._render_deploy_stage()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.app.mdl.bind(deploy_status=self.on_deploy_status)
        self.app.mdl.bind(is_ready=self.app_state_refresh)

    def on_deploy_status(
        self, view: "ApplicationsScreenView", status: Optional[dict[str, Any]]
    ) -> None:
        if status:
            self.ids.txt_deployment_data.text = json.dumps(status, indent=4)

    def select_path(self, path: str) -> None:
        """
        It will be called when the user clicks on the file name
        or the catalog selection button.

        :param path: path to the selected directory or file;
        """
        if validate_app_file(Path(path)):
            self.app_file_valid = True
            self.ids.app_file.accept_path(path)
            self.dismiss_message()
        else:
            self.app_file_valid = False
            self.display_error("Invalid AOT-compiled module file")

    def _render_deploy_stage(self) -> None:
        layout: MDGridLayout = self.ids.layout_status

        # pre-emptive cleanup
        layout.clear_widgets()
        icon_box = MDAnchorLayout(
            size_hint_x=None,
            width=32,
        )

        if self.model.deploy_stage is None:
            layout.add_widget(MDLabel(text="N/A"))

        elif self.model.deploy_stage == DeployStage.Error:
            icon_box.add_widget(MDIcon(icon="alert-circle"))
            layout.add_widget(icon_box)
            layout.add_widget(MDLabel(text="Error"))

        elif self.model.deploy_stage in (
            DeployStage.WaitFirstStatus,
            DeployStage.WaitAppliedConfirmation,
        ):
            icon_box.add_widget(
                Image(
                    source=resource_path("assets/spinner.gif"),
                    size_hint_y=None,
                    height=24,
                )
            )
            layout.add_widget(icon_box)
            layout.add_widget(MDLabel(text="Deploying..."))

        elif self.model.deploy_stage == DeployStage.Done:
            icon_box.add_widget(MDIcon(icon="check-circle"))
            layout.add_widget(icon_box)
            layout.add_widget(MDLabel(text="Complete"))
