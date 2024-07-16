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
from abc import ABC
from typing import Any
from typing import Callable
from typing import Optional

from kivy.event import EventDispatcher
from kivy.uix.widget import Widget
from local_console.core.camera import CameraState
from local_console.utils.tracking import TrackingVariable


class CameraStateProxyBase(ABC, EventDispatcher):
    """
    Framework class for establishing event dispatching on changes
    to data in the underlying logical state of the program.

    This abstract class is intended to be subclassed and having
    added Kivy Properties as class attributes.
    """

    def bind_proxy_to_state(
        self,
        property_name: str,
        state: CameraState,
        transform: Optional[Callable] = None,
    ) -> None:
        """
        Makes a binding for enabling the Kivy app to dispatch observers
        from updates to camera state properties that are not set by the
        camera, but either by the user or the GUI itself (i.e. computed
        properties)

        The optional 'transform' argument enables providing a custom
        conversion function (e.g. converting from str to Path).
        """
        assert hasattr(self, property_name)
        assert hasattr(state, property_name)
        state_variable = getattr(state, property_name)
        assert isinstance(state_variable, TrackingVariable)

        def binding(_me: type[CameraStateProxyBase], value: Any) -> None:
            state_variable.value = value if not transform else transform(value)

        bind = {property_name: binding}
        self.bind(**bind)

    def bind_state_to_proxy(
        self,
        property_name: str,
        state: CameraState,
        transform: Callable = lambda v: v,
    ) -> None:
        """
        Makes a binding for propagating an update to a TrackingVariable
        in CameraState, to its corresponding property in the proxy. This
        is useful for maintaining a GUI state consistent with the logical
        state of the camera.

        The optional 'transform' argument enables providing a custom
        conversion function (e.g. converting from Path to str).
        """
        assert hasattr(self, property_name)
        assert hasattr(state, property_name)
        state_variable = getattr(state, property_name)
        assert isinstance(state_variable, TrackingVariable)

        def update_proxy(current: Optional[Any], previous: Optional[Any]) -> None:
            setattr(self, property_name, transform(current))

        state_variable.subscribe(update_proxy)
