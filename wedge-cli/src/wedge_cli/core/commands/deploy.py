import enum
import hashlib
import json
import logging
import uuid
from abc import abstractmethod
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import Optional

import trio
import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.enums import ModuleExtension
from wedge_cli.core.enums import Target
from wedge_cli.core.schemas import DeploymentManifest
from wedge_cli.core.schemas import OnWireProtocol
from wedge_cli.servers.webserver import AsyncWebserver

logger = logging.getLogger(__name__)


async def exec_deployment(
    agent: Agent,
    deploy_manifest: DeploymentManifest,
    deploy_webserver: bool,
    webserver_path: Path,
    webserver_port: int,
    timeout_secs: int,
) -> bool:
    deploy_fsm: DeployFSM = (
        EVP1DeployFSM(agent, deploy_manifest)
        if agent.onwire_schema == OnWireProtocol.EVP1
        else EVP2DeployFSM(agent, deploy_manifest)
    )

    # GUI mode starts responding to requests in the background, but not the CLI
    # NOTE: revisit GUI - CLI interaction
    await agent.initialize_handshake()

    success = False
    with trio.move_on_after(timeout_secs) as timeout_scope:
        assert agent.onwire_schema  # make mypy happy
        logger.debug(f"Opening webserver at {webserver_path}")
        async with (
            agent.mqtt_scope([MQTTTopics.ATTRIBUTES.value]),
            AsyncWebserver(webserver_path, webserver_port, None, deploy_webserver),
        ):
            assert agent.nursery is not None  # make mypy happy
            agent.nursery.start_soon(deploy_fsm.message_task)
            await deploy_fsm.done.wait()
            success = True

    if timeout_scope.cancelled_caught:
        logger.error("Timeout when sending modules.")

    return success


class DeployStage(enum.IntEnum):
    WaitFirstStatus = enum.auto()
    WaitAppliedConfirmation = enum.auto()
    Done = enum.auto()


class DeployFSM:
    def __init__(self, agent: Agent, to_deploy: DeploymentManifest) -> None:
        self.agent = agent
        self.to_deploy = to_deploy

        self.stage = DeployStage.WaitFirstStatus
        self.done = trio.Event()

    @abstractmethod
    async def update(self, deploy_status: dict[str, Any]) -> None:
        """
        Updates Deployment.

        Notes:
        - Assumes that requests have been processed
        """
        pass

    def verify_report(self, deploy_status: dict[str, Any]) -> tuple[bool, bool]:
        matches = self.to_deploy.deployment.deploymentId == deploy_status.get(
            "deploymentId"
        )
        is_finished = deploy_status.get("reconcileStatus") == "ok"
        return is_finished, matches

    @abstractmethod
    async def message_task(self) -> None:
        """
        Receives reports from the agent and applies changes accordingly.
        """
        pass


class EVP2DeployFSM(DeployFSM):
    async def update(self, deploy_status: Optional[dict[str, Any]]) -> None:
        assert isinstance(deploy_status, dict)

        next_stage = self.stage

        is_finished, matches = self.verify_report(deploy_status)
        if is_finished and matches:
            self.stage = DeployStage.Done
            logger.info("Deployment complete")
            self.done.set()
            return

        if self.stage == DeployStage.WaitFirstStatus:
            logger.debug("Agent can receive deployments. Pushing manifest now.")
            await self.agent.deploy(self.to_deploy)
            next_stage = DeployStage.WaitAppliedConfirmation

        elif self.stage == DeployStage.WaitAppliedConfirmation:
            if matches:
                logger.debug(
                    "Deployment received, reconcile=%s",
                    deploy_status.get("reconcileStatus", "<null>"),
                )
                logger.info("Deployment received, waiting for reconcile completion")

        elif self.stage == DeployStage.Done:
            logger.warning(
                "Should not reach here! (status is %s)",
                json.dumps(deploy_status),
            )

        self.stage = next_stage

    async def message_task(self) -> None:
        """
        Notes:
        - Assumes report interval is short to perform the handshake.
        """
        assert self.agent.client is not None
        async with self.agent.client.messages() as mgen:
            async for msg in mgen:
                payload = json.loads(msg.payload)
                logger.debug("Incoming on %s: %s", msg.topic, str(payload))

                if payload and msg.topic == MQTTTopics.ATTRIBUTES.value:
                    if "deploymentStatus" in payload:
                        deploy_status = payload.get("deploymentStatus")
                        await self.update(deploy_status)


class EVP1DeployFSM(DeployFSM):
    async def update(self, deploy_status: dict[str, Any]) -> None:
        """
        Sending deployment is done in message_task.
        This method waits until current deployment in agent matches deployed.
        """
        is_finished, matches = self.verify_report(deploy_status)
        if is_finished and matches:
            logger.info("Deployment complete")
            self.done.set()
            return

    async def message_task(self) -> None:
        """
        Simplified handshake compared to EVP2:
        - Sends deployment at beginning.
        - Check current is the one applied.
        """
        assert self.agent.client is not None

        # Deploy without comparing with current to speed-up the process
        await self.agent.deploy(self.to_deploy)
        async with self.agent.client.messages() as mgen:
            async for msg in mgen:
                payload = json.loads(msg.payload)
                logger.debug("Incoming on %s: %s", msg.topic, str(payload))

                if payload and msg.topic == MQTTTopics.ATTRIBUTES.value:
                    if "deploymentStatus" in payload:
                        deploy_status = json.loads(payload.get("deploymentStatus"))
                        await self.update(deploy_status)


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

        if use_signed and target_arch:
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
