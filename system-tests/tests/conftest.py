import shutil
from collections.abc import Generator
from pathlib import Path

import allure
import pytest
from src.agent import T3P
from src.lc_adapter import LocalConsoleAdapter

from tests.utils import Options


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
    broker = LocalConsoleAdapter(options.onwire_schema, options.certs_folder)

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

    if not options.local:
        agent = T3P(
            options.devispare_host,
            options.devispare_token,
        )

        try:
            agent.run(
                tmp_dir,
                options.devispare_firmware,
                options.frp_host,
                options.frp_port_mqtt,
                mqtt_broker.cafile,
                certfile,
                keyfile,
                options.onwire_schema,
            )

            if not mqtt_broker.is_device_connected.wait(timeout=5 * 60):
                raise Exception("Device not connected to the MQTT Broker")

            yield

        finally:
            agent.stop(logs_folder=results_folder)

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
