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
from pathlib import Path

from local_console.gui.view.base_screen import BaseScreenView


class ConfigurationScreenView(BaseScreenView):

    def model_is_changed(self) -> None:
        """
        Called whenever any change has occurred in the data model.
        The view in this method tracks these changes and updates the UI
        according to these changes.
        """

        self.ids.schema_pick.accept_path(
            ""
            if self.model.flatbuffers_schema is None
            else str(self.model.flatbuffers_schema)
        )
        self.ids.app_configuration_pick.accept_path(
            ""
            if self.model.app_configuration is None
            else str(self.model.app_configuration)
        )
        self.ids.labels_pick.accept_path(
            "" if self.model.app_labels is None else str(self.model.app_labels)
        )
