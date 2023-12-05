import configparser
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from pydantic import ValidationError
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import DeploymentManifest
from wedge_cli.utils.schemas import EVPParams
from wedge_cli.utils.schemas import IPAddress
from wedge_cli.utils.schemas import MQTTParams
from wedge_cli.utils.schemas import WebserverParams

logger = logging.getLogger(__name__)


def get_default_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["evp"] = {
        "iot_platform": "tb",
        "version": "EVP2",
    }
    config["mqtt"] = {"host": "localhost", "port": "1883", "device_id": ""}
    config["webserver"] = {"host": "localhost", "port": "8000"}
    return config


def setup_default_config() -> None:
    config_file = config_paths.config_path
    if not config_file.is_file():
        logger.info("Generating default config_paths")
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.error(f"Error while generating folder {config_file.parent}")
            exit(1)
        with open(config_paths.config_path, "w") as f:
            get_default_config().write(f)


def parse_ini(config_parser: configparser.ConfigParser) -> str:
    parsed_config = ["\n"]
    for section in config_parser.sections():
        parsed_config.append(f"[{section}]")
        for key, value in config_parser.items(section):
            parsed_config.append(f"{key} = {value}")
    return "\n".join(parsed_config)


def config_to_schema(config: configparser.ConfigParser) -> AgentConfiguration:
    try:
        return AgentConfiguration(
            evp=EVPParams(
                iot_platform=config["evp"]["iot_platform"],
                version=config["evp"]["version"],
            ),
            mqtt=MQTTParams(
                host=IPAddress(ip_value=config["mqtt"]["host"]),
                port=int(config["mqtt"]["port"]),
                device_id=config["mqtt"].get("device_id", None),
            ),
            webserver=WebserverParams(
                host=IPAddress(ip_value=config["webserver"]["host"]),
                port=int(config["webserver"]["port"]),
            ),
        )
    except KeyError as e:
        logger.error(
            f"Config file not correct. Section or parameter missing is {e}. \n The file should have the following sections and parameters {parse_ini(get_default_config())}"
        )
        exit(1)


def get_config(config_file: Path = config_paths.config_path) -> AgentConfiguration:
    config_parser: configparser.ConfigParser = configparser.ConfigParser()
    try:
        config_parser.read(config_file)
    except FileNotFoundError:
        logger.error("Config file not found")
        exit(1)
    except configparser.MissingSectionHeaderError:
        logger.error("No header found in the specified file")
        exit(1)
    return config_to_schema(config_parser)


def get_deployment_schema() -> DeploymentManifest:
    try:
        with open(config_paths.deployment_json) as f:
            deployment_data = json.load(f)
    except Exception:
        logger.error("deployment.json does not exist or not well defined")
        exit(1)
    try:
        return DeploymentManifest(**deployment_data)
    except ValidationError as e:
        missing_field = list(e.errors()[0]["loc"])[1:]
        logger.warning(f"Missing field in the deployment manifest: {missing_field}")
        exit(1)


def get_empty_deployment() -> str:
    deployment = {
        "deployment": {
            "deploymentId": str(uuid.uuid4()),
            "instanceSpecs": {},
            "modules": {},
            "publishTopics": {},
            "subscribeTopics": {},
        }
    }
    return json.dumps(deployment)


def check_section_and_params(
    agent_config: AgentConfiguration, section: str, parameter: Optional[str] = None
) -> None:
    if section not in agent_config.__dict__.keys():
        logger.error(f"Invalid section. Valid ones are: {agent_config.__dict__.keys()}")
        raise ValueError

    if parameter and parameter not in agent_config.model_dump()[f"{section}"].keys():
        logger.error(
            f"Invalid parameter of the {section} section. Valid ones are: {list(agent_config.model_dump()[f'{section}'].keys())}"
        )
        raise ValueError


def parse_section_to_ini(
    section_model: BaseModel, section_name: str, parameter: Optional[str] = None
) -> str:
    ini_lines = [f"[{section_name}]"]
    if parameter:
        parameter_value = section_model.__dict__[f"{parameter}"]
        if parameter == "host":
            ini_lines.append(f"{parameter} = {parameter_value.ip_value}")
        else:
            ini_lines.append(f"{parameter} = {parameter_value}")
    else:
        for field, value in section_model.__dict__.items():
            if field == "host":
                ini_lines.append(f"{field} = {value.ip_value}")
            else:
                ini_lines.append(f"{field} = {value}")

    return "\n".join(ini_lines)


def schema_to_parser(
    agent_config: AgentConfiguration, section: str, parameter: str, new: str
) -> configparser.ConfigParser:
    if parameter == "port":
        try:
            int(new)
        except ValueError as e:
            logger.error("Port specified not int number")
            raise e
    config_dict = agent_config.model_dump()
    config_dict[section][parameter] = new
    config_parser = configparser.ConfigParser()
    for section_names, values in config_dict.items():
        if "host" in values.keys():
            if isinstance(values["host"], dict):
                values["host"] = values["host"]["ip_value"]
        config_parser[section_names] = values
    return config_parser
