from local_console.core.schemas.edge_cloud_if_v1 import OTA
from local_console.core.schemas.edge_cloud_if_v1 import Version
from pydantic import BaseModel


class OtaData(BaseModel):
    OTA: OTA
    Version: Version
