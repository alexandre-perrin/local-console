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
import json
import logging
import sys
from functools import partial
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Callable
from typing import Optional

import trio
import typer
from local_console.clients.agent import Agent
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import MQTTTopics
from local_console.core.commands.deploy import DeployFSM
from local_console.core.commands.deploy import get_empty_deployment
from local_console.core.commands.deploy import manifest_setup_epilog
from local_console.core.config import config_obj
from local_console.core.enums import config_paths
from local_console.core.enums import ModuleExtension
from local_console.core.enums import Target
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase
from local_console.servers.webserver import SyncWebserver
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.local_network import is_localhost

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(help="Command for deploying application to the agent")
def deploy(
    empty: Annotated[
        bool,
        typer.Option(
            "-e",
            "--empty",
            help="Option to remove previous deployment with an empty one",
        ),
    ] = False,
    signed: Annotated[
        bool,
        typer.Option(
            "-s",
            "--signed",
            help="Option to deploy signed files (already built with the 'build' command)",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "-t",
            "--timeout",
            help="Set timeout to wait for the modules to be downloaded by the agent",
        ),
    ] = 15,
    target: Annotated[
        Optional[Target],
        typer.Argument(
            help="Optional argument to specify which AoT compilation to deploy. If not defined it will deploy the plain WASM"
        ),
    ] = None,
    force_webserver: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force-webserver",
            help=(
                "If passed, the command will deploy the webserver locally, even if the "
                "configured webserver host does not resolve to localhost"
            ),
        ),
    ] = False,
) -> None:
    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)
    local_ip = get_my_ip_by_routing()

    port = 0
    host_override: Optional[str] = None

    deploy_webserver = force_webserver
    device_config = config_obj.get_active_device_config()
    configured_host = device_config.webserver.host
    if is_localhost(configured_host) or configured_host == local_ip:
        deploy_webserver = True
    else:
        host_override = configured_host
        port = device_config.webserver.port

    deploy_fsm = DeployFSM.instantiate(
        schema,
        agent.deploy,
        None,
        deploy_webserver,
        port,
        timeout,
    )

    if empty:
        deployment_manifest = get_empty_deployment()
    else:
        bin_fp = Path.cwd() / config_paths.bin
        if not bin_fp.is_dir():
            raise Exception(f"'bin' folder does not exist at {bin_fp.parent}")

        deployment_manifest = multiple_module_manifest_setup(
            bin_fp,
            deploy_fsm.webserver,
            target,
            signed,
            port,
            host_override,
        )
        Path(config_paths.deployment_json).write_text(
            json.dumps(deployment_manifest.model_dump(), indent=2)
        )

    try:
        success = False
        deploy_fsm.set_manifest(deployment_manifest)
        deployment_fn = partial(
            exec_deployment,
            agent,
            deploy_fsm,
        )
        success = trio.run(deployment_fn)

    except Exception as e:
        logger.exception("Deployment error", exc_info=e)
    except KeyboardInterrupt:
        logger.info("Cancelled by the user")
    finally:
        sys.exit(0 if success else 1)


class DeployCommand(PluginBase):
    implementer = app


def multiple_module_manifest_setup(
    files_dir: Path,
    webserver: SyncWebserver,
    target_arch: Optional[Target],
    use_signed: bool,
    port_override: Optional[int] = None,
    host_override: Optional[str] = None,
) -> DeploymentManifest:
    """
    Fill all fields in of a preliminary deployment manifest that
    comes with a set of modules specified, having their file paths
    set in the corresponding module's `downloadUrl` field.

    All module files must be located in `files_dir`
    """
    assert files_dir.is_dir()
    webserver.set_directory(files_dir)
    manifest = config_obj.get_deployment()
    mod_identifiers = list(manifest.deployment.modules.keys())
    for ident in mod_identifiers:
        manifest.deployment.modules[ident].downloadUrl = str(
            project_binary_lookup(files_dir, ident, target_arch, use_signed)
        )

    return manifest_setup_epilog(
        files_dir, manifest, webserver, port_override, host_override
    )


def project_binary_lookup(
    files_dir: Path,
    module_base_name: str,
    target_arch: Optional[Target],
    use_signed: bool,
) -> Path:
    """
    Looks for a built WASM module file that is named by following the
    file naming convention selected at the command line by the flags.
    """
    assert files_dir.is_dir()

    name_parts: list[str] = [module_base_name]
    if target_arch:
        name_parts += [target_arch.value, ModuleExtension.AOT.value]
    else:
        name_parts.append(ModuleExtension.WASM.value)

    if use_signed and target_arch:
        name_parts.append(ModuleExtension.SIGNED.value)

    binary = files_dir / ".".join(name_parts)
    if not binary.is_file():
        raise FileNotFoundError(f"{binary} not found.")

    if use_signed and not target_arch:
        logger.warning(
            f"There is no target architecture, the {binary} module to be deployed is not signed"
        )

    return binary


async def exec_deployment(
    agent: Agent,
    deploy_fsm: DeployFSM,
    stage_callback: Optional[Callable[[DeployStage], None]] = None,
) -> bool:
    assert agent.onwire_schema
    success = False

    # Ensure device readiness to receive a deployment manifest
    await agent.initialize_handshake()

    async with (
        trio.open_nursery() as nursery,
        agent.mqtt_scope([MQTTTopics.ATTRIBUTES.value]),
    ):

        # assert agent.nursery
        deploy_loop = partial(stimuli_loop, agent, deploy_fsm)
        nursery.start_soon(deploy_loop)

        await deploy_fsm.start(nursery)
        await deploy_fsm.done.wait()
        success = not deploy_fsm.errored
        nursery.cancel_scope.cancel()

    return success


async def stimuli_loop(agent: Agent, fsm: DeployFSM) -> None:
    """
    Used to stimulate a deployment FSM, calling its update()
    method with deployment status updates as they come.
    """
    assert agent.client is not None

    async with agent.client.messages() as mgen:
        async for msg in mgen:
            payload = json.loads(msg.payload)
            await stimulus_proc(msg.topic, payload, agent.onwire_schema, fsm)


async def stimulus_proc(
    topic: str,
    payload: dict[str, Any],
    onwire_schema: Optional[OnWireProtocol],
    fsm: DeployFSM,
) -> None:
    if (
        payload
        and topic == MQTTTopics.ATTRIBUTES.value
        and "deploymentStatus" in payload
    ):
        deploy_status_repr = payload.get("deploymentStatus", {})
        if onwire_schema == OnWireProtocol.EVP1 or onwire_schema is None:
            deploy_status = json.loads(deploy_status_repr)
        else:
            deploy_status = deploy_status_repr

        logger.debug("Deploy: %s", deploy_status)
        await fsm.update(deploy_status)  # type: ignore  # mypy is not seeing the argument???
