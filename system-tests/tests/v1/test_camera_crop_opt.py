import allure
from src.lc_adapter import LocalConsoleAdapter

from tests.matchers.is_equal import equal_to


@allure.parent_suite("Module Direct Command")
@allure.suite("Camera Crop Opt")
def test_change_value(mqtt_broker: LocalConsoleAdapter) -> None:
    allure.dynamic.title("Change Value - Onwire: EVP1 - Interface v1")

    mqtt_broker.publish_mdc(
        "backdoor-EA_Main",
        "SetCameraCropOptValue",
        {
            "CropOptValue": 100,
        },
    )

    mqtt_broker.wait_mdc_response(
        equal_to(
            {"Result": "Succeeded"},
        ),
        timeout=30,
    )

    mqtt_broker.publish_mdc("backdoor-EA_Main", "GetCameraCropOptValue", {})

    mqtt_broker.wait_mdc_response(
        equal_to(
            {"Result": "Succeeded", "CropOptValue": 100},
        ),
        timeout=30,
    )
