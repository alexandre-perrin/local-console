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
import shutil
from collections.abc import Generator
from pathlib import Path

import allure
import pytest
from devicetools import DeviSpareClient
from src.lc_adapter import LocalConsoleAdapter

from tests.utils import Options

BASE_DIR = Path(__file__).parent


def pytest_addoption(parser: pytest.Parser) -> None:
    for opt, args in Options.get():
        parser.addoption(f"--{opt.replace('_', '-')}", **args)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    options = Options.load(config)

    # Allure uses item name as ID
    # IDs must be different to merge
    # multiple runs into one report
    # (e.g. Onwire Version evp1/evp2)

    for item in items:
        item.name = f"onwire_{options.onwire_version}_{item.name}"
        item.originalname = f"onwire_{options.onwire_version}_{item.originalname}"


@pytest.fixture(scope="session", autouse=True)
@allure.title("Load Test Configuration")
def options(request: pytest.FixtureRequest) -> Options:
    options = Options.load(request.config)
    options.verify()
    return options


@pytest.fixture(scope="session", autouse=True)
@allure.title("Create Results Folder")
def results_folder() -> Path:
    results_folder = Path("results")
    if results_folder.is_dir():
        shutil.rmtree(results_folder)
    results_folder.mkdir()
    return results_folder


@pytest.fixture(scope="session", autouse=True)
@allure.title("Create Data (tmp) Folder")
def tmp_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp: Path = tmp_path_factory.mktemp("data")
    return tmp


@pytest.fixture(scope="session", autouse=True)
@allure.title("Start MQTT Broker")
def mqtt_broker(options: Options, results_folder: Path, tmp_dir: Path) -> Generator:
    broker = LocalConsoleAdapter(
        options.onwire_schema, options.certs_folder, options.signing_key
    )

    try:
        broker.start(
            options.local,
            options.frp_host,
            options.frp_port_mqtt,
            options.frp_token,
            options.frp_port_http,
            options.frp_name_suffix,
        )

        yield broker

    finally:
        broker.stop(logs_folder=results_folder)


@pytest.fixture(scope="session", autouse=True)
@allure.title("Start Agent")
def _agent(
    options: Options,
    results_folder: Path,
    tmp_dir: Path,
    mqtt_broker: LocalConsoleAdapter,
) -> Generator:
    certfile = options.certs_folder / "client.crt"
    keyfile = options.certs_folder / "client.key"
    https_ca_cert = BASE_DIR.joinpath("../src/resources/mozilla-root-ca.pem").resolve()

    if not options.local:
        client = DeviSpareClient(
            options.devispare_host,
            options.devispare_token,
        )
        device = client.t3p_device(
            b_bootloader=options.bin_bootloader,
            b_partitions=options.bin_partitions,
            b_nuttx=options.bin_system,
        )

        try:
            device.run(
                options.frp_host,
                options.frp_port_mqtt,
                options.onwire_schema.platform,
                mqtt_broker.cafile,
                certfile,
                keyfile,
                https_ca_cert,
            )

            if not mqtt_broker.is_device_connected.wait(timeout=5 * 60):
                raise Exception("Device not connected to the MQTT Broker")

            yield

        finally:
            device.stop()
            device.save_logs(results_folder)

    else:
        print("\n\nMQTT\n")
        print("· Host: mqtt.local")
        print("· Port: 8883")
        print(f"· CA:\n\n{mqtt_broker.cafile.read_text()}")
        print("Device\n")
        print(f"· Platform: {options.onwire_schema.platform}")
        print(f"· Public Certificate:\n\n{certfile.read_text()}")
        print(f"· Private Certificate:\n\n{keyfile.read_text()}")
        print("Waiting Device to be connected to the MQTT Broker ...")

        if not mqtt_broker.is_device_connected.wait(timeout=5 * 60):
            raise Exception("Device not connected to the MQTT Broker")

        yield
