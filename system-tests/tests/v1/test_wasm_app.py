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
from random import sample

import allure
from hamcrest import has_entries
from hamcrest import has_entry
from src.lc_adapter import LocalConsoleAdapter


@allure.parent_suite("WASM Application life cycle")
@allure.suite("Deployment")
def test_wasm_deployment(mqtt_broker: LocalConsoleAdapter) -> None:
    allure.dynamic.title("WASM module - Onwire: EVP1 - Interface v1")

    # Set EVP1
    mqtt_broker.invoke_cli("config", "set", "evp", "iot_platform", "evp1")

    root_dir = Path(__file__).parents[3]
    sample_projects_dir = root_dir / "samples"

    # First deploy the simplest app
    app_dir = sample_projects_dir / "simplest"
    mqtt_broker.build_module(app_dir)
    deploy = mqtt_broker.deploy_module(app_dir)
    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"

    # then, clear deployment
    deploy = mqtt_broker.empty_deployment()
    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"

    # then, deploy the a more complex app
    app_dir = sample_projects_dir / "rpc-example"
    mqtt_broker.build_module(app_dir)
    deploy = mqtt_broker.deploy_module(app_dir)
    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"

    # test a MDC-telemetry message processing loop:
    # 1. generate a random RGB color
    random_color = dict(zip("rgb", sample(range(256), k=3)))
    # 2. compose the command payload and send
    mdc_payload = "".join(f"{random_color[color]:02X}" for color in "rgb")
    mqtt_broker.publish_mdc("node", "my-method", {"rgb": mdc_payload})
    # 3. compose the expected result payload and wait
    tel_payload = {color: str(val) for color, val in random_color.items()}
    mqtt_broker.wait_telemetry(
        has_entry(
            "node/my-topic",
            has_entries(tel_payload),
        ),
        timeout=60,
    )
