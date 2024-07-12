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
from typing import Optional

from hypothesis import given
from local_console.core.camera import CameraState
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.camera_proxy import CameraStateProxy

from tests.strategies.configs import generate_valid_device_configuration


def test_simple_property_binding():

    camera_proxy = CameraStateProxy()

    callback_state = {"callback_called": False, "instance": None, "value": None}

    def callback(instance: CameraStateProxy, value: str, state: dict) -> None:
        state["callback_called"] = True
        state["instance"] = instance
        state["value"] = value

    # Use simple binding, as provided by Kivy
    camera_proxy.bind(
        image_dir_path=lambda instance, value: callback(instance, value, callback_state)
    )
    # Update the property value
    camera_proxy.image_dir_path = "new value"

    # Assert the callback was called
    assert callback_state["callback_called"] is True
    assert callback_state["instance"] == camera_proxy
    assert callback_state["value"] == "new value"


def test_proxy_to_state_binding():
    """
    This test shows how to perform a proxy-->state data binding,
    by means of the bind_proxy_to_state() method of CameraProxy.

    This is useful for propagating updates of user-facing widgets'
    values into camera state variables.
    """

    camera_proxy = CameraStateProxy()

    camera_state = CameraState()
    assert camera_state.ai_model_file.previous is None
    assert camera_state.ai_model_file.value is None

    # Use bind_proxy_to_state to connect to the camera_state
    camera_proxy.bind_proxy_to_state("ai_model_file", camera_state, Path)
    # Update the property value on the proxy
    some_path = Path.cwd()
    camera_proxy.ai_model_file = str(some_path)

    # The value must have been set in the camera state's variable
    assert camera_state.ai_model_file.value == some_path
    assert camera_state.ai_model_file.previous is None


@given(generate_valid_device_configuration())
def test_state_to_proxy_binding(a_device_config):
    """
    This test shows how to perform a state-->proxy data binding,
    by means of the subscribe() method of TrackingVariable members
    in CameraState.

    This is useful for propagating messages issued by the camera
    into GUI widgets that are data-bound via proxy properties.
    """

    camera_proxy = CameraStateProxy()
    camera_state = CameraState()

    # Use a callback and subscribe() on a TrackingVariable member of CameraState
    def update_proxy(
        current: Optional[DeviceConfiguration], previous: Optional[DeviceConfiguration]
    ) -> None:
        camera_proxy.device_config = current

    camera_state.device_config.subscribe(update_proxy)

    # Update the property value
    camera_state.device_config.value = a_device_config

    # The value must have been set in the proxy property
    assert camera_proxy.device_config == a_device_config
