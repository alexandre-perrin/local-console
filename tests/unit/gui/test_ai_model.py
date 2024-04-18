from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from wedge_cli.gui.controller.ai_model_screen import AIModelScreenController
from wedge_cli.gui.controller.ai_model_screen import get_package_hash
from wedge_cli.utils.local_network import get_my_ip_by_routing


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


@pytest.fixture(params=["000001"])
def network_id(request):
    return request.param


@pytest.mark.trio
async def test_undeploy_step_rpc_sent(network_id: str):
    mock_model = AsyncMock()
    mock_model.ota_event = AsyncMock()
    mock_driver = MagicMock()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with patch("wedge_cli.gui.controller.ai_model_screen.AIModelScreenView"), patch(
        "wedge_cli.gui.controller.ai_model_screen.Agent", return_value=mock_agent
    ):
        mock_model.device_config.OTA.UpdateStatus = "Done"
        controller = AIModelScreenController(mock_model, mock_driver)
        await controller.undeploy_step(network_id)
        payload = (
            f'{{"OTA":{{"UpdateModule":"DnnModel","DeleteNetworkID":"{network_id}"}}}}'
        )
        mock_agent.configure.assert_called_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )


@pytest.mark.trio
async def test_undeploy_step_not_deployed_model(update_status: str):
    mock_model = AsyncMock()
    mock_model.ota_event = AsyncMock()
    mock_driver = MagicMock()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with patch("wedge_cli.gui.controller.ai_model_screen.AIModelScreenView"), patch(
        "wedge_cli.gui.controller.ai_model_screen.Agent", return_value=mock_agent
    ):
        mock_model.device_config.OTA.UpdateStatus = update_status
        controller = AIModelScreenController(mock_model, mock_driver)
        await controller.undeploy_step("000001")
        mock_model.ota_event.assert_not_awaited()


@pytest.mark.trio
async def test_deploy_step(tmp_path, network_id, update_status: str):
    filename = "dummy.bin"
    tmp_file = tmp_path / filename

    mock_model = AsyncMock()
    mock_model.ota_event = AsyncMock()
    mock_driver = MagicMock()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with (
        patch("wedge_cli.gui.controller.ai_model_screen.AIModelScreenView"),
        patch(
            "wedge_cli.gui.controller.ai_model_screen.Agent", return_value=mock_agent
        ),
        patch(
            "wedge_cli.gui.controller.ai_model_screen.AsyncWebserver",
            return_value=mock_agent,
        ),
        patch(
            "wedge_cli.gui.controller.ai_model_screen.get_network_ids",
            return_value=[network_id],
        ),
    ):
        mock_model.device_config.OTA.UpdateStatus = update_status
        controller = AIModelScreenController(mock_model, mock_driver)
        with open(tmp_file, "w") as f:
            f.write("dummy")
        await controller.deploy_step(network_id, tmp_file)
        hashvalue = get_package_hash(tmp_file)
        payload = (
            '{"OTA":{"UpdateModule":"DnnModel","DesiredVersion":"",'
            f'"PackageUri":"http://{get_my_ip_by_routing()}:8000/dummy.bin",'
            f'"HashValue":"{hashvalue}"'
            "}}"
        )
        mock_agent.configure.assert_called_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )
        mock_model.ota_event.assert_not_awaited()
