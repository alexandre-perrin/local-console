import base64
import json
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from paho.mqtt.client import MQTT_ERR_ERRNO
from paho.mqtt.client import MQTT_ERR_SUCCESS
from wedge_cli.clients.agent import Agent
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.core.schemas import OnWireProtocol

from tests.strategies.configs import generate_agent_config


@given(st.text(), st.text(), st.text(), generate_agent_config())
@pytest.mark.trio
async def test_configure_instance_evp1(
    instance_id: str, topic: str, config: str, agent_config: AgentConfiguration
):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
        patch("wedge_cli.clients.agent.Agent.publish"),
    ):
        agent = Agent()
        agent.onwire_schema = OnWireProtocol.EVP1
        async with agent.mqtt_scope([]):
            await agent.configure(instance_id, topic, config)
            agent.async_done()

        payload = json.dumps(
            {
                f"configuration/{instance_id}/{topic}": base64.b64encode(
                    config.encode("utf-8")
                ).decode("utf-8")
            }
        )
        agent.publish.assert_called_once_with(
            MQTTTopics.ATTRIBUTES.value, payload=payload
        )


@given(st.text(), st.text(), st.text(), generate_agent_config())
@pytest.mark.trio
async def test_configure_instance_evp2(
    instance_id: str, topic: str, config: str, agent_config: AgentConfiguration
):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
        patch("wedge_cli.clients.agent.Agent.publish"),
    ):
        agent = Agent()
        agent.onwire_schema = OnWireProtocol.EVP2
        async with agent.mqtt_scope([]):
            await agent.configure(instance_id, topic, config)
        payload = json.dumps({f"configuration/{instance_id}/{topic}": config})
        agent.publish.assert_called_once_with(
            MQTTTopics.ATTRIBUTES.value, payload=payload
        )


@given(st.text(), generate_agent_config())
@pytest.mark.trio
async def test_rpc(instance_id: str, agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        method = "$agent/set"
        params = '{"log_enable": true}'
        agent = Agent()
        async with agent.mqtt_scope([]):
            agent.client.publish_and_wait = AsyncMock(
                return_value=(MQTT_ERR_SUCCESS, None)
            )
            await agent.rpc(instance_id, method, params)
            agent.async_done()

        agent.client.publish_and_wait.assert_called_once()


@given(st.text(), generate_agent_config())
@pytest.mark.trio
async def test_rpc_error(instance_id: str, agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        method = "$agent/set"
        params = '{"log_enable": true}'
        agent = Agent()
        async with agent.mqtt_scope([]):
            agent.client.publish_and_wait = AsyncMock(
                return_value=(MQTT_ERR_ERRNO, None)
            )
            with pytest.raises(ConnectionError):
                await agent.rpc(instance_id, method, params)
            agent.async_done()

        agent.client.publish_and_wait.assert_called_once()


@given(generate_agent_config())
def test_get_deployment(agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        agent = Agent()
        agent._loop_forever = Mock()
        agent._on_message_print_payload = Mock()
        agent.get_deployment()
        agent._loop_forever.assert_called_once_with(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=agent._on_message_print_payload.return_value,
        )
        agent._on_message_print_payload.assert_called_once()


@given(generate_agent_config())
def test_get_telemetry(agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        agent = Agent()
        agent._loop_forever = Mock()
        agent._on_message_telemetry = Mock()
        agent.get_telemetry()
        agent._loop_forever.assert_called_once_with(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=agent._on_message_telemetry.return_value,
        )
        agent._on_message_telemetry.assert_called_once()


@given(st.text(min_size=1, max_size=5), generate_agent_config())
def test_get_instance(instance_id: str, agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        agent = Agent()
        agent._loop_forever = Mock()
        agent._on_message_instance = Mock()
        agent.get_instance(instance_id)
        agent._loop_forever.assert_called_once_with(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=agent._on_message_instance.return_value,
        )
        agent._on_message_instance.assert_called_once_with(instance_id)


@given(st.text(min_size=1, max_size=5), st.integers(), generate_agent_config())
def test_get_logs(instance_id: str, timeout: int, agent_config: AgentConfiguration):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        agent = Agent()
        agent._loop_forever = Mock()
        agent._on_message_logs = Mock()
        agent.get_instance_logs(instance_id, timeout)
        agent._loop_forever.assert_called_once_with(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=agent._on_message_logs.return_value,
        )
        agent._on_message_logs.assert_called_once_with(instance_id, timeout)
