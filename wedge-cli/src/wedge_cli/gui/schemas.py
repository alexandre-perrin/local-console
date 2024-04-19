from pydantic import BaseModel
from wedge_cli.core.schemas.edge_cloud_if_v1 import OTA
from wedge_cli.core.schemas.edge_cloud_if_v1 import Version


class OtaData(BaseModel):
    OTA: OTA
    Version: Version
