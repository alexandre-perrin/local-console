from base64 import b64encode
from pathlib import Path
from pathlib import PurePosixPath

from cryptography.hazmat.primitives import hashes
from local_console.core.schemas.edge_cloud_if_v1 import DnnModelVersion
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody


def get_package_hash(package_file: Path) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(package_file.read_bytes())
    return b64encode(digest.finalize()).decode()


def get_package_version(package_file: Path) -> str:
    ver_bytes = package_file.read_bytes()[0x30:0x40]
    return ver_bytes.decode()


def get_network_id(package_file: Path) -> str:
    ver_bytes = get_package_version(package_file)
    return ver_bytes[6 : 6 + 6]


def configuration_spec(
    package_file: Path, webserver_root: Path, webserver_port: int, webserver_host: str
) -> DnnOta:
    file_hash = get_package_hash(package_file)
    version_str = get_package_version(package_file)
    rel_path = PurePosixPath(package_file.relative_to(webserver_root))
    url = f"http://{webserver_host}:{webserver_port}/{rel_path}"
    return DnnOta(
        OTA=DnnOtaBody(DesiredVersion=version_str, PackageUri=url, HashValue=file_hash)
    )


def get_network_ids(dnn_model_version: DnnModelVersion) -> list[str]:
    return [desired_version[6 : 6 + 6] for desired_version in dnn_model_version]
