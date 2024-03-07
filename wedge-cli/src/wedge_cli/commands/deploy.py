import enum
import hashlib
import json
import logging
import sys
import uuid
from pathlib import Path
from pathlib import PurePosixPath
from typing import Annotated
from typing import Any
from typing import Optional
from typing import Union

import trio
import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.clients.agent import check_attributes_request
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.config import get_config
from wedge_cli.core.config import get_deployment_schema
from wedge_cli.core.enums import config_paths
from wedge_cli.core.enums import ModuleExtension
from wedge_cli.core.enums import Target
from wedge_cli.core.schemas import DeploymentManifest
from wedge_cli.core.schemas import OnWireProtocol
from wedge_cli.servers.webserver import AsyncWebserver
from wedge_cli.utils.local_network import get_my_ip_by_routing
from wedge_cli.utils.local_network import is_localhost

logger = logging.getLogger(__name__)

app = typer.Typer(help="Command for deploying application to the agent")


@app.callback(invoke_without_command=True)
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
            help="Option to deploy signed files(already built with the 'build' command)",
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
) -> None:
    config: AgentConfiguration = get_config()  # type:ignore
    port = config.webserver.port
    host = config.webserver.host.ip_value
    deploy_webserver = False

    local_ip = get_my_ip_by_routing()
    if is_localhost(host) or host == local_ip:
        host = local_ip
        deploy_webserver = True

    agent = Agent()
    if empty:
        deployment_manifest = get_empty_deployment()
    else:
        bin_fp = Path(config_paths.bin)
        if not bin_fp.is_dir():
            raise SystemExit(f"'bin' folder does not exist at {bin_fp.parent}")

        deployment_manifest = get_deployment_schema()
        update_deployment_manifest(deployment_manifest, host, port, bin_fp, target, signed)  # type: ignore
        with open(config_paths.deployment_json, "w") as f:
            json.dump(deployment_manifest.model_dump(), f, indent=2)

        make_unique_module_ids(deployment_manifest)

    success = False
    try:
        success = trio.run(
            exec_deployment, agent, deployment_manifest, deploy_webserver, port, timeout
        )
    except Exception as e:
        logger.exception("Deployment error", exc_info=e)
    except KeyboardInterrupt:
        logger.info("Cancelled by the user")
    finally:
        sys.exit(0 if success else 1)


async def exec_deployment(
    agent: Agent,
    deploy_manifest: DeploymentManifest,
    deploy_webserver: bool,
    webserver_port: int,
    timeout_secs: int,
) -> bool:
    success = False
    subscription_topics = [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
    deploy_fsm = DeployFSM(agent, deploy_manifest)
    with trio.move_on_after(timeout_secs) as timeout_scope:
        assert agent.onwire_schema  # make mypy happy
        async with (
            agent.mqtt_scope(subscription_topics),
            AsyncWebserver(Path.cwd(), webserver_port, None, deploy_webserver),
        ):
            assert agent.nursery is not None  # make mypy happy
            agent.nursery.start_soon(deploy_fsm.message_task)
            agent.nursery.start_soon(deploy_fsm.initialization_timeout)
            await deploy_fsm.done.wait()
            success = True
            agent.async_done()

    if timeout_scope.cancelled_caught:
        logger.error("Timeout when sending modules.")

    return success


class DeployStage(enum.IntEnum):
    MaybeAttributesResponse = enum.auto()
    SentAttributesResponse = enum.auto()
    WaitFirstStatus = enum.auto()
    WaitAppliedConfirmation = enum.auto()
    Done = enum.auto()


class DeployFSM:
    def __init__(self, agent: Agent, to_deploy: DeploymentManifest) -> None:
        self.agent = agent
        self.to_deploy = to_deploy

        self.stage = DeployStage.MaybeAttributesResponse
        self.done = trio.Event()

    async def update(
        self, deploy_status: Optional[Union[str, dict[str, Any]]], got_request: bool
    ) -> None:
        next_stage = self.stage

        if got_request:
            next_stage = DeployStage.SentAttributesResponse
        else:
            assert isinstance(deploy_status, dict)
            is_finished, matches = self.verify_report(deploy_status)
            if is_finished and matches:
                next_stage = DeployStage.Done
                logger.info("Deployment complete")
                self.done.set()
            else:
                if self.stage == DeployStage.MaybeAttributesResponse:
                    next_stage = DeployStage.WaitFirstStatus

                elif self.stage == DeployStage.SentAttributesResponse:
                    next_stage = DeployStage.WaitFirstStatus

                elif self.stage == DeployStage.WaitFirstStatus:
                    logger.debug("Agent can receive deployments. Pushing manifest now.")
                    await self.agent.deploy(self.to_deploy)
                    next_stage = DeployStage.WaitAppliedConfirmation

                elif self.stage == DeployStage.WaitAppliedConfirmation:
                    if matches:
                        logger.debug(
                            "Deployment received, reconcile=%s",
                            deploy_status.get("reconcileStatus", "<null>"),
                        )
                        logger.info(
                            "Deployment received, waiting for reconcile completion"
                        )

                elif self.stage == DeployStage.Done:
                    logger.warning(
                        "Should not reach here! (status is %s)",
                        json.dumps(deploy_status),
                    )

        self.stage = next_stage

    def verify_report(self, deploy_status: dict[str, Any]) -> tuple[bool, bool]:
        matches = self.to_deploy.deployment.deploymentId == deploy_status.get(
            "deploymentId"
        )
        is_finished = deploy_status.get("reconcileStatus") == "ok"
        return is_finished, matches

    async def message_task(self) -> None:
        assert self.agent.client is not None
        async with self.agent.client.messages() as mgen:
            async for msg in mgen:
                payload = json.loads(msg.payload)
                logger.debug("Incoming on %s: %s", msg.topic, str(payload))

                got_request = await check_attributes_request(
                    self.agent, msg.topic, payload
                )

                deploy_status: Optional[Union[str, dict[str, Any]]] = None
                if payload and msg.topic == MQTTTopics.ATTRIBUTES.value:
                    deploy_status = payload.get("deploymentStatus")
                    if (
                        deploy_status is not None
                        and self.agent.onwire_schema == OnWireProtocol.EVP1
                    ):
                        # it comes stringified, see:
                        # https://github.com/midokura/wedge-agent/blob/fa3d4840c37978938084cbc70612fdb8ea8dbf9f/src/libwedge-agent/report.c#L192
                        deploy_status = json.loads(str(deploy_status))

                if deploy_status or got_request:
                    await self.update(deploy_status, got_request)

    async def initialization_timeout(self, timeout: int = 10) -> None:
        # This check can be made early just because the agent object
        # has .onwire_schema initialized during object construction
        if self.agent.onwire_schema != OnWireProtocol.EVP1:
            return

        await trio.sleep(timeout)
        if self.stage < DeployStage.WaitFirstStatus:
            logger.warning(
                "Device did not issue an update in the timeout period. Pushing the deployment anyways."
            )
            # Force start deployment push
            self.stage = DeployStage.WaitFirstStatus
            await self.update({}, False)


def make_unique_module_ids(deploy_man: DeploymentManifest) -> None:
    """
    Makes module identifiers in the deployment manifest unique
    across deployments, by suffixing them with a slice of the
    module's hash.
    """
    modules = deploy_man.deployment.modules
    old_to_new = {name: f"{name}-{m.hash[:5]}" for name, m in modules.items()}

    # Update modules
    for old_id, new_id in old_to_new.items():
        module = modules.pop(old_id)
        modules[new_id] = module

    # Update instanceSpecs
    instances = deploy_man.deployment.instanceSpecs
    for instance in instances.values():
        instance.moduleId = old_to_new[instance.moduleId]


def get_empty_deployment() -> DeploymentManifest:
    deployment = {
        "deployment": {
            "deploymentId": str(uuid.uuid4()),
            "instanceSpecs": {},
            "modules": {},
            "publishTopics": {},
            "subscribeTopics": {},
        }
    }
    return DeploymentManifest.model_validate(deployment)


def update_deployment_manifest(
    deployment_manifest: DeploymentManifest,
    host: str,
    port: int,
    files_dir: Path,
    target_arch: Optional[Target],
    use_signed: bool,
) -> None:
    for module in deployment_manifest.deployment.modules.keys():
        wasm_file = files_dir / f"{module}.{ModuleExtension.WASM}"
        if not wasm_file.is_file():
            logger.error(
                f"{wasm_file} not found. Please build the modules before deployment"
            )
            raise typer.Exit(code=1)

        name_parts = [module]
        if target_arch:
            name_parts += [target_arch.value, ModuleExtension.AOT.value]
        else:
            name_parts.append(ModuleExtension.WASM.value)

        if use_signed:
            if target_arch:
                name_parts.append(ModuleExtension.SIGNED.value)

        file = files_dir / ".".join(name_parts)

        if use_signed and not target_arch:
            logger.warning(
                f"There is no target architecture, the {file} module to be deployed is not signed"
            )

        # use the downloadUrl field as placeholder, read from the function below
        deployment_manifest.deployment.modules[module].downloadUrl = str(file)

    populate_urls_and_hashes(deployment_manifest, host, port, files_dir.parent)


def calculate_sha256(path: Path) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(path.read_bytes())
    return sha256_hash.hexdigest()


def populate_urls_and_hashes(
    deployment_manifest: DeploymentManifest,
    host: str,
    port: int,
    root_path: Path,
) -> None:
    for module in deployment_manifest.deployment.modules.keys():
        file = Path(deployment_manifest.deployment.modules[module].downloadUrl)
        deployment_manifest.deployment.modules[module].hash = calculate_sha256(file)
        deployment_manifest.deployment.modules[
            module
        ].downloadUrl = (
            f"http://{host}:{port}/{PurePosixPath(file.relative_to(root_path))}"
        )

    # DeploymentId based on deployment manifest content
    deployment_manifest.deployment.deploymentId = ""
    deployment_manifest_hash = hashlib.sha256(
        str(deployment_manifest.model_dump()).encode("utf-8")
    )
    deployment_manifest.deployment.deploymentId = deployment_manifest_hash.hexdigest()
