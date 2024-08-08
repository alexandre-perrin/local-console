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
from pathlib import Path

import pytest
import trio
from hypothesis import given
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.config import config_obj
from local_console.gui.model.camera_proxy import CameraStateProxy

from tests.fixtures.camera import cs_init
from tests.fixtures.camera import cs_init_context
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


@pytest.mark.trio
async def test_proxy_to_state_binding(cs_init) -> None:
    """
    This test shows how to perform a proxy-->state data binding,
    by means of the bind_proxy_to_state() method of CameraProxy.

    This is useful for propagating updates of user-facing widgets'
    values into camera state variables.
    """

    camera_proxy = CameraStateProxy()
    camera_state = cs_init

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


@pytest.mark.trio
async def test_bind_connections(cs_init) -> None:
    camera_proxy = CameraStateProxy()
    camera_state = cs_init

    camera_proxy.bind_connections(camera_state)
    camera_state.initialize_connection_variables(
        "tb", config_obj.get_active_device_config()
    )

    # The value must have been set in the camera state's variable
    assert camera_proxy.mqtt_host == "localhost"
    assert camera_proxy.mqtt_port == "1883"
    assert camera_proxy.ntp_host == "pool.ntp.org"
    assert camera_proxy.ip_address == ""
    assert camera_proxy.subnet_mask == ""
    assert camera_proxy.gateway == ""
    assert camera_proxy.dns_server == ""
    assert camera_proxy.wifi_ssid == ""
    assert camera_proxy.wifi_password == ""
    assert not camera_proxy.is_connected


@pytest.mark.trio
async def test_bind_core_variables(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_core_variables(camera_state)
    camera_state.is_ready.value = True

    # The value must have been set in the camera state's variable
    assert camera_proxy.is_ready
    assert not camera_proxy.is_streaming
    assert camera_proxy.device_config is not None


@pytest.mark.trio
async def test_bind_stream_variables(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_stream_variables(camera_state)

    camera_proxy.roi = ((0, 0), (0.5, 0.5))
    camera_state.stream_status.value = StreamStatus.Active

    assert camera_state.roi.value == camera_proxy.roi
    assert camera_proxy.stream_status == StreamStatus.Active


@pytest.mark.trio
async def test_bind_ai_model_function(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_ai_model_function(camera_state)

    camera_proxy.ai_model_file = "testing_path"
    camera_state.ai_model_file_valid = True

    assert camera_state.ai_model_file.value == Path("testing_path")
    assert not camera_proxy.ai_model_file_valid


@pytest.mark.trio
async def test_bind_firmware_file_functions(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_firmware_file_functions(camera_state)

    camera_state.firmware_file_valid.value = True

    camera_proxy.firmware_file = str(Path("testing_path"))
    camera_proxy.firmware_file_version = "0.0.0"
    camera_proxy.firmware_file_type = OTAUpdateModule.APFW

    assert camera_state.firmware_file.value == Path("testing_path")
    assert camera_state.firmware_file_version.value == "0.0.0"
    assert camera_state.firmware_file_type.value == OTAUpdateModule.APFW
    assert not camera_proxy.firmware_file_valid
    assert camera_proxy.firmware_file_hash == ""


@pytest.mark.trio
async def test_bind_vapp_file_functions(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_vapp_file_functions(camera_state)

    camera_proxy.vapp_config_file = Path("testing_path")
    camera_proxy.vapp_labels_file = Path("testing_path")
    camera_proxy.vapp_type = "type_test"

    camera_state.vapp_labels_map.value = {0: "test"}

    assert camera_state.vapp_config_file.value == Path("testing_path")
    assert camera_state.vapp_labels_file.value == Path("testing_path")
    assert camera_state.vapp_type.value == "type_test"
    assert camera_proxy.vapp_labels_map == str({0: "test"})


@pytest.mark.trio
async def test_bind_app_module_functions(cs_init) -> None:
    camera_state = cs_init
    camera_proxy = CameraStateProxy()

    camera_proxy.bind_app_module_functions(camera_state)

    camera_state.deploy_status.value = {0: "test"}
    camera_state.deploy_stage.value = DeployStage.WaitAppliedConfirmation
    camera_state.deploy_operation.value = DeploymentType.Application

    camera_proxy.module_file = str(Path("test_path"))

    assert camera_proxy.deploy_stage == DeployStage.WaitAppliedConfirmation
    assert camera_proxy.deploy_status == json.dumps({0: "test"}, indent=4)
    assert camera_proxy.deploy_operation == DeploymentType.Application
    assert camera_state.module_file.value == Path("test_path")


@pytest.mark.trio
@given(generate_valid_device_configuration())
async def test_state_to_proxy_binding(a_device_config):
    """
    This test shows how to perform a state-->proxy data binding,
    by means of the subscribe() method of TrackingVariable members
    in CameraState.

    This is useful for propagating messages issued by the camera
    into GUI widgets that are data-bound via proxy properties.
    """
    async with (
        trio.open_nursery() as nursery,
        cs_init_context() as camera_state,
    ):
        camera_proxy = CameraStateProxy()

        # Use bind_state_to_proxy to connect to the camera_state
        camera_proxy.bind_state_to_proxy("device_config", camera_state)
        # Update the state variable
        camera_state.device_config.value = a_device_config

        # The value must have been set in the proxy property
        assert camera_proxy.device_config == a_device_config
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_state_to_proxy_binding_reassignment(tmp_path_factory, cs_init) -> None:
    """
    This test serves to make sure further updates to the
    state variable will be reflected on the proxy property
    """

    camera_proxy = CameraStateProxy()
    camera_state = cs_init

    # Value binding
    camera_proxy.bind_state_to_proxy("ai_model_file", camera_state, str)

    # Update the state variable
    first_dir = tmp_path_factory.mktemp("first")
    camera_state.ai_model_file.value = first_dir
    assert camera_proxy.ai_model_file == str(first_dir)

    # Second update
    second_dir = tmp_path_factory.mktemp("second")
    camera_state.ai_model_file.value = second_dir
    assert camera_proxy.ai_model_file == str(second_dir)


@pytest.mark.trio
async def test_state_to_proxy_binding_with_observer(tmp_path_factory, cs_init) -> None:
    """
    This test serves to see a binding of an observer callback
    to a proxy property that is bound to a state variable in action.
    """

    camera_proxy = CameraStateProxy()
    camera_state = cs_init

    callback_state = {"was_called": False, "instance": None, "value": None}

    def callback(value: str, state: dict) -> None:
        state["was_called"] = True
        state["value"] = value

    # State->Proxy value binding
    camera_proxy.bind_state_to_proxy("ai_model_file_valid", camera_state)

    # Bind an observer callback
    camera_proxy.bind(
        ai_model_file_valid=lambda instance, value: callback(value, callback_state)
    )

    assert not callback_state["was_called"]

    # Update the state variable
    new_value = False
    camera_state.ai_model_file_valid.value = new_value

    assert camera_proxy.ai_model_file_valid == new_value
    assert callback_state["was_called"]
    callback_state["value"] == new_value

    # Check behavior of further updates
    callback_state["was_called"] = False
    new_value = True
    camera_state.ai_model_file_valid.value = new_value
    assert camera_proxy.ai_model_file_valid == new_value
    assert callback_state["was_called"]
    callback_state["value"] == new_value


def test_difference_of_property_with_force_dispatch(tmp_path):
    """
    This test shows an important behavior difference of Kivy Property
    instances, chosen with the optional boolean force_dispatch flag:

    - By default, when a Kivy property (used here as proxy property)
      is assigned a value, it compares it with its current value, and
      only if they differ, then it will dispatch any bound callbacks.

    - However, if the property is defined with force_dispatch=True,
      then the comparison is not made, so dispatching takes place even
      when the property is assigned a value it currently has.

    Reference:
    https://github.com/kivy/kivy/blob/a4c48b1fbb0a329b8e6f1b81004268c4aa1d05af/kivy/properties.pyx#L329
    """

    camera_proxy = CameraStateProxy()

    def observer(value: bool, pilot: dict) -> None:
        pilot["was_called"] = True
        pilot["value"] = value

    #### Start test of a default property (i.e. force_dispatch = False)

    camera_proxy.create_property("unforced_prop", False)

    test_pilot = {"was_called": False, "value": None}

    camera_proxy.bind(unforced_prop=lambda instance, value: observer(value, test_pilot))

    # initial condition
    test_pilot["was_called"] = False
    assert not camera_proxy.unforced_prop

    # first assignment with a different value, no surprises here
    camera_proxy.unforced_prop = True
    assert test_pilot["was_called"]
    assert test_pilot["value"]

    # next assignment with _the same_ value: observer was NOT called!
    test_pilot["was_called"] = False
    camera_proxy.unforced_prop = True
    assert not test_pilot["was_called"]

    del test_pilot
    #### Start test of a "forced" property (i.e. force_dispatch = True)

    camera_proxy.create_property("forced_prop", False, force_dispatch=True)

    test_pilot = {"was_called": False, "value": None}

    camera_proxy.bind(forced_prop=lambda instance, value: observer(value, test_pilot))

    # initial condition
    test_pilot["was_called"] = False
    assert not camera_proxy.forced_prop

    # first assignment with a different value, no surprises here
    camera_proxy.forced_prop = True
    assert test_pilot["was_called"]
    assert test_pilot["value"]

    # next assignment with _the same_ value: observer WAS called!
    test_pilot["was_called"] = False
    camera_proxy.forced_prop = True
    assert test_pilot["was_called"]
