import enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.clients.webserver import _WebServer
from wedge_cli.utils.config import get_config
from wedge_cli.utils.config import get_deployment_schema
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import ModuleExtension
from wedge_cli.utils.enums import Target
from wedge_cli.utils.schemas import DeploymentManifest


logger = logging.getLogger(__name__)

app = typer.Typer(help="Command for deploying application to the agent")


def deploy_empty(agent: Agent) -> None:
    deployment = get_empty_deployment()
    agent.deploy(deployment=deployment)


def deploy_manifest(
    agent: Agent,
    deployment_manifest: DeploymentManifest,
    signed: bool,
    timeout: int,
    target: Optional[Target],
) -> None:
    bin_fp = Path(config_paths.bin)
    if not bin_fp.exists():
        logger.warning("bin folder does not exist")
        exit(1)

    webserver = _WebServer(agent)
    webserver.update_deployment_manifest(deployment_manifest, target, signed)  # type: ignore
    num_modules = len(deployment_manifest.deployment.modules.keys())
    webserver.start(num_modules, timeout)  # type: ignore
    make_unique_module_ids(deployment_manifest)
    agent.deploy(json.dumps(deployment_manifest.model_dump()))
    webserver.close()


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
    ] = 10,
    target: Annotated[
        Optional[Target],
        typer.Argument(
            help="Optional argument to specify which AoT compilation to deploy. If not defined it will deploy the plain WASM"
        ),
    ] = None,
) -> None:
    agent = Agent()
    if empty:
        deploy_empty(agent=agent)
        return

    deployment_manifest = get_deployment_schema()

    deploy_manifest(
        agent=agent,
        deployment_manifest=deployment_manifest,
        signed=signed,
        timeout=timeout,
        target=target,
    )


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
            exit(1)

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

        deployment_manifest.deployment.modules[module].hash = calculate_sha256(file)
        deployment_manifest.deployment.modules[
            module
        ].downloadUrl = f"http://{host}:{port}/{file}"

    with open(config_paths.deployment_json, "w") as f:
        json.dump(deployment_manifest.model_dump(), f, indent=2)


def calculate_sha256(path: Path) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(path.read_bytes())
    return sha256_hash.hexdigest()
