from pathlib import Path

import allure
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


    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"
