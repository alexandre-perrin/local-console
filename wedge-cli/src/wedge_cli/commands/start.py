import logging
import os
import shutil
from ctypes import cdll
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Annotated
from typing import Optional

import typer
from cryptography.exceptions import InvalidSignature
from cryptography.x509 import load_pem_x509_certificate
from pydantic import ValidationError
from wedge_cli.clients.listener import Listener
from wedge_cli.core.config import get_config
from wedge_cli.core.enums import Commands
from wedge_cli.core.enums import config_paths
from wedge_cli.core.enums import EVPEnvVars
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.core.schemas import IPAddress
from wedge_cli.core.schemas import Libraries
from wedge_cli.core.schemas import RemoteConnectionInfo
from wedge_cli.core.schemas import TLSConfiguration
from wedge_cli.utils.local_network import is_localhost
from wedge_cli.utils.tls import ensure_certificate_pair_exists
from wedge_cli.utils.tls import get_certificate_cn
from wedge_cli.utils.tls import get_random_identifier
from wedge_cli.utils.tls import get_remote_server_certificate
from wedge_cli.utils.tls import verify_certificate_against_ca

logger = logging.getLogger(__name__)
app = typer.Typer(help="Command that starts the agent up")


def start_agent(connection_info: RemoteConnectionInfo, libraries: Libraries) -> int:
    if not None in connection_info.__dict__.values():
        server = Listener(
            ip=connection_info.host, port=connection_info.port  # type:ignore
        )
        server.open_listener()
        server.receive_config()

    retcode = 1
    try:
        config: AgentConfiguration = get_config()
        agent_env = get_agent_environment(config)
        agent_command = get_agent_command_parts(libraries)

        if config.is_tls_enabled and is_localhost(config.mqtt.host.ip_value):
            # TLS with the MQTT broker running in localhost!
            # Comply with TLS' Subject Common Name (CN) matching
            # by first acquiring the server's CN...
            server_cn = ensure_tls_setup(config)
            # ... then connecting under patched named resolution:
            run_agent_tls_with_custom_localhost(agent_command, agent_env, server_cn)
        else:
            logger.debug(f"Running: {' '.join(agent_command)}")
            run(agent_command, env=agent_env, check=True)
        retcode = 0
    except FileNotFoundError:
        logger.error("evp_agent not in PATH")
    except InvalidSignature as e:
        logger.error(f"Certificate is not signed by the configured CA: {e}")
    except ConnectionError as e:
        logger.error(f"TLS error: {e}")
    except KeyboardInterrupt:
        logger.debug("Terminated by SIGTERM")
        retcode = 0
    except SystemExit as e:
        logger.debug("Terminated by SIGINT")
        raise e

    return retcode


def ensure_tls_setup(config: AgentConfiguration) -> str:
    # Verify TLS setup is sane (certificates validate against configured CA)
    server_cert = get_remote_server_certificate(config.mqtt.host, config.mqtt.port)
    assert config.tls.ca_certificate  # make mypy happy
    ca_cert = load_pem_x509_certificate(config.tls.ca_certificate.read_bytes())
    verify_certificate_against_ca(server_cert, ca_cert)

    client_cert = load_pem_x509_certificate(
        config_paths.agent_cert_pair[0].read_bytes()
    )
    verify_certificate_against_ca(client_cert, ca_cert)

    server_cn = get_certificate_cn(server_cert)
    assert server_cn  # make mypy happy
    return server_cn


def get_agent_command_parts(libraries: Libraries) -> list[str]:
    agent_path = shutil.which(Commands.EVP_AGENT.value)
    if not agent_path:
        raise FileNotFoundError("evp_agent not in PATH")

    command = [
        str(agent_path),
    ]

    if libraries.libraries:
        for l in libraries.libraries:
            command.append("-l")
            command.append(l)  # type:ignore

    return command


def get_agent_environment(config: AgentConfiguration) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            EVPEnvVars.EVP_IOT_PLATFORM: config.evp.iot_platform,
            EVPEnvVars.EVP_MQTT_HOST: config.mqtt.host.ip_value,
            EVPEnvVars.EVP_MQTT_PORT: str(config.mqtt.port),
            EVPEnvVars.EVP_DATA_DIR: str(config_paths.evp_data_path),  # type:ignore
            EVPEnvVars.EVP_HTTPS_CA_CERT: str(
                config_paths.https_ca_path
            ),  # type:ignore
            EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC: "3",
        }
    )

    if config.is_tls_enabled:
        device_cert_path, device_key_path = get_device_tls_data(
            config.mqtt.device_id, config.tls
        )
        env[EVPEnvVars.EVP_MQTT_TLS_CLIENT_CERT] = str(device_cert_path)
        env[EVPEnvVars.EVP_MQTT_TLS_CLIENT_KEY] = str(device_key_path)
        assert config.tls.ca_certificate  # make mypy happy
        env[EVPEnvVars.EVP_MQTT_TLS_CA_CERT] = str(config.tls.ca_certificate)
    else:
        device_id: Optional[str] = config.mqtt.device_id
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = (
            device_id if device_id else get_random_identifier("agent-", 7)
        )

    return env


def get_device_tls_data(
    specified_id: Optional[str], tls_configuration: TLSConfiguration
) -> tuple[Path, Path]:
    if specified_id:
        logger.info(
            "Specified optional device id will be used as its client certificate's Common Name (CN)"
        )
        device_id = specified_id
    else:
        device_id = get_random_identifier("agent-")

    base_file_name = "agent"
    cert_file = config_paths.tls_cert_root / f"{base_file_name}.crt.pem"
    key_file = config_paths.tls_cert_root / f"{base_file_name}.key.pem"
    ensure_certificate_pair_exists(device_id, cert_file, key_file, tls_configuration)

    return cert_file, key_file


def run_agent_tls_with_custom_localhost(
    agent_command: list[str], agent_env: dict[str, str], custom_localhost: str
) -> None:
    """
    This function checks whether the machine can use cwrap's
    nss_wrapper to run the agent with patched name resolution,
    enabling it to verify the server certificate presented by
    the local MQTT broker. If available, it launches the agent
    under nss_wrapper's preload with a temporary custom hosts file.
    """

    nss_wrapper = "libnss_wrapper.so"
    try:
        cdll.LoadLibrary(nss_wrapper)
    except OSError:
        raise SystemExit(
            "cwrap's nss_wrapper library was not found. Please "
            "install it in order to launch the agent in TLS mode "
            "as it tries to connect to the local MQTT broker"
        )

    with TemporaryDirectory() as tempdir:
        # Create custom hosts file
        custom_hosts_file = Path(tempdir) / "hosts"
        with custom_hosts_file.open("w") as f:
            f.write(f"127.0.0.1 {custom_localhost}\n")

        # Set nss_wrapper up for launching the agent
        agent_env["LD_PRELOAD"] = nss_wrapper
        agent_env["NSS_WRAPPER_HOSTS"] = str(custom_hosts_file)

        # Use the same custom hostname as the MQTT host
        agent_env[EVPEnvVars.EVP_MQTT_HOST] = custom_localhost

        logger.debug(f"Running: {' '.join(agent_command)}")
        run(agent_command, env=agent_env, check=True)


@app.callback(invoke_without_command=True)
def start(
    remote: Annotated[
        tuple[str, int],
        typer.Option(
            help="Start the agent waiting for the configuration to be sent. Need to specify host and port: "
            "e.g. --remote localhost 8001"
        ),
    ] = (  # type: ignore
        None,
        None,
    ),
    libraries: Annotated[
        Optional[list[str]],
        typer.Option(
            "--library",
            "-l",
            help="Library to be loaded by the agent ",
        ),
    ] = [],
) -> None:
    if remote[0]:
        try:
            ip_value = IPAddress(ip_value=remote[0])
        except ValueError:
            logger.warning(f"Invalid host {remote[0]}. Send a valid ip")
            raise typer.Exit(code=1)
    else:
        ip_value = None
    try:
        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=ip_value, port=remote[1]),  # type: ignore
            libraries=Libraries(libraries=libraries),  # type: ignore
        )  # type:ignore
        exit(rc)
    except ValidationError as e:
        logger.warning(
            f"Error with parameter {e.errors()[0]['loc'][0]}. {e.errors()[0]['msg']}"
        )
