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

from hypothesis import given
from local_console.core.camera.state import CameraState
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

    # Use bind_state_to_proxy to connect to the camera_state
    camera_proxy.bind_state_to_proxy("device_config", camera_state)
    # Update the state variable
    camera_state.device_config.value = a_device_config

    # The value must have been set in the proxy property
    assert camera_proxy.device_config == a_device_config


def test_state_to_proxy_binding_reassignment(tmp_path_factory):
    """
    This test serves to make sure further updates to the
    state variable will be reflected on the proxy property
    """

    camera_proxy = CameraStateProxy()
    camera_state = CameraState()

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


def test_state_to_proxy_binding_with_observer(tmp_path_factory):
    """
    This test serves to see a binding of an observer callback
    to a proxy property that is bound to a state variable in action.
    """

    camera_proxy = CameraStateProxy()
    camera_state = CameraState()

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
