from unittest.mock import patch

import hypothesis.strategies as st
from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.qr import app
from wedge_cli.core.schemas import AgentConfiguration

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number

runner = CliRunner()


@given(generate_agent_config())
def test_qr_with_defaults(config: AgentConfiguration) -> None:
    with (
        patch("wedge_cli.commands.qr.get_config", return_value=config),
        patch("wedge_cli.commands.qr.is_localhost", return_value=False),
        patch("wedge_cli.commands.qr.get_my_ip_by_routing", return_value="1.2.3.4"),
        patch("wedge_cli.core.camera.qr_string", return_value="") as mock_qr_string,
    ):
        result = runner.invoke(app, [])
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            config.mqtt.host.ip_value,
            config.mqtt.port,
            config.is_tls_enabled,
            "pool.ntp.org",
            "",
            "",
            "",
            "",
        )


@given(
    generate_agent_config(),
    generate_valid_ip(),
    generate_valid_port_number(),
    st.booleans(),
    generate_valid_ip(),
)
def test_qr_with_overrides(
    config: AgentConfiguration,
    host_override: str,
    port_override: int,
    tls_enable_override: bool,
    ntp_override: str,
) -> None:
    with (
        patch("wedge_cli.commands.qr.get_config", return_value=config),
        patch("wedge_cli.commands.qr.is_localhost", return_value=False),
        patch("wedge_cli.commands.qr.get_my_ip_by_routing", return_value="1.2.3.4"),
        patch("wedge_cli.core.camera.qr_string", return_value="") as mock_qr_string,
    ):
        result = runner.invoke(
            app,
            [
                "--host",
                host_override,
                "--port",
                port_override,
                f"--{'' if tls_enable_override else 'no-'}enable-tls",
                "--ntp-server",
                ntp_override,
            ],
        )
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            host_override,
            port_override,
            tls_enable_override,
            ntp_override,
            "",
            "",
            "",
            "",
        )


@given(generate_agent_config(), generate_valid_ip())
def test_qr_for_local_host(config: AgentConfiguration, local_host_alias: str) -> None:
    """
    This test showcases how the command will generate the QR with the host set to the
    IP address that a camera could use over the local network, when the specified host
    is determined to match localhost.
    """
    with (
        patch("wedge_cli.commands.qr.get_config", return_value=config),
        patch("wedge_cli.commands.qr.is_localhost", return_value=True),
        patch("wedge_cli.commands.qr.get_my_ip_by_routing", return_value="1.2.3.4"),
        patch("wedge_cli.core.camera.qr_string", return_value="") as mock_qr_string,
    ):
        result = runner.invoke(app, ["--host", local_host_alias])
        assert result.exit_code == 0

        mock_qr_string.assert_called_once_with(
            "1.2.3.4",
            config.mqtt.port,
            config.is_tls_enabled,
            "pool.ntp.org",
            "",
            "",
            "",
            "",
        )
