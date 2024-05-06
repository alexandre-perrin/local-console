import base64
import json

from devispare import EvpIotPlatform


class OnwireVersion:
    EVP1 = "evp1"
    EVP2 = "evp2"


VERSION_TO_PLATFORM: dict[str, EvpIotPlatform] = {
    OnwireVersion.EVP1: EvpIotPlatform.EVP1,
    OnwireVersion.EVP2: EvpIotPlatform.TB,
}


class OnWireSchema:
    def __init__(self, onwire_version: str) -> None:
        try:
            self._schema = VERSION_TO_SCHEMA[onwire_version]
            self.platform = VERSION_TO_PLATFORM[onwire_version]

        except KeyError as err:
            raise Exception("Invalid Platform") from err

    def to_config(
        self, reqid: int | str, instance: str, topic: str, config: dict
    ) -> dict:
        return self._schema.to_config(str(reqid), instance, topic, config)

    def from_config(self, config: dict) -> dict:
        return self._schema.from_config(config)

    def to_rpc(
        self, reqid: int | str, instance: str, method: str, params: dict
    ) -> dict:
        return {
            "method": "ModuleMethodCall",
            "params": self._schema.to_direct_command_request(
                str(reqid), instance, method, params
            ),
        }

    def from_rpc(self, res: dict) -> dict:
        return self._schema.from_direct_command_response(res)


class BaseOnWireSchema:
    @staticmethod
    def to_config(reqid: str, instance: str, topic: str, config: dict) -> dict:
        raise NotImplementedError

    @staticmethod
    def from_config(config: dict) -> dict:
        raise NotImplementedError

    @staticmethod
    def from_direct_command_response(res: dict) -> dict:
        raise NotImplementedError

    @staticmethod
    def to_direct_command_request(
        reqid: str, instance: str, method: str, params: dict
    ) -> dict:
        raise NotImplementedError


class OnWireSchemaEVP1(BaseOnWireSchema):
    @staticmethod
    def to_config(reqid: str, instance: str, topic: str, config: dict) -> dict:
        return {
            f"configuration/{instance}/{topic}": base64.b64encode(
                json.dumps(config).encode()
            ).decode()
        }

    @staticmethod
    def from_direct_command_response(res: dict) -> dict:
        return dict(res["response"])

    @staticmethod
    def to_direct_command_request(
        reqid: str, instance: str, method: str, params: dict
    ) -> dict:
        return {
            "moduleMethod": method,
            "moduleInstance": instance,
            "params": params,
        }


class OnWireSchemaEVP2(BaseOnWireSchema):
    @staticmethod
    def to_config(reqid: str, instance: str, topic: str, config: dict) -> dict:
        return {
            f"configuration/{instance}/{topic}": json.dumps(config),
            "req_info": {"req_id": reqid},
        }

    @staticmethod
    def from_config(config: dict) -> dict:
        for key in config:
            if type(config[key]) in [str, bytes, bytearray]:
                config[key] = json.loads(config[key])
        return config

    @staticmethod
    def from_direct_command_response(res: dict) -> dict:
        return dict(json.loads(res["direct-command-response"]["response"]))

    @staticmethod
    def to_direct_command_request(
        reqid: str, instance: str, method: str, params: dict
    ) -> dict:
        return {
            "direct-command-request": {
                "reqid": reqid,
                "method": method,
                "instance": instance,
                "params": json.dumps(
                    {
                        **params,
                        "req_info": {"req_id": reqid},
                    }
                ),
            }
        }


VERSION_TO_SCHEMA: dict[str, type[BaseOnWireSchema]] = {
    OnwireVersion.EVP1: OnWireSchemaEVP1,
    OnwireVersion.EVP2: OnWireSchemaEVP2,
}
