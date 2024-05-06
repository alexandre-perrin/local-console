import allure
from src.lc_adapter import LocalConsoleAdapter

from tests.matchers.is_equal import equal_to


@allure.parent_suite("Module Direct Command")
@allure.suite("Reboot")
def test_reboot(mqtt_broker: LocalConsoleAdapter) -> None:
    allure.dynamic.title("Reboot - Onwire: EVP1 - Interface v1")

    mqtt_broker.publish_mdc(
        "backdoor-EA_Main",
        "Reboot",
        {},
    )

    mqtt_broker.wait_mdc_response(
        equal_to(
            {"Result": "Accepted"},
        ),
        timeout=30,
    )

    mqtt_broker.is_device_connected.clear()

    assert mqtt_broker.is_device_connected.wait(
        timeout=2 * 60
    ), "Device not connected after reboot"
