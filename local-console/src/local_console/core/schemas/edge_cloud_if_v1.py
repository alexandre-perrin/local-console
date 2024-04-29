"""
Edge Cloud IF v1 schemas. Properties not included here are ignored. For example, PQ settings.
"""
from local_console.utils.schemas import ListModel
from pydantic import BaseModel
from pydantic import Field


class Hardware(BaseModel):
    Sensor: str
    SensorId: str
    KG: str
    ApplicationProcessor: str
    LedOn: bool


class DnnModelVersion(ListModel):
    root: list[str]


class Version(BaseModel):
    SensorFwVersion: str
    SensorLoaderVersion: str
    DnnModelVersion: DnnModelVersion
    ApFwVersion: str
    ApLoaderVersion: str


class Status(BaseModel):
    Sensor: str
    ApplicationProcessor: str


class OTA(BaseModel):
    SensorFwLastUpdatedDate: str
    SensorLoaderLastUpdatedDate: str
    DnnModelLastUpdatedDate: list[str]
    ApFwLastUpdatedDate: str
    UpdateProgress: int
    UpdateStatus: str


class Permission(BaseModel):
    FactoryReset: bool


class DeviceConfiguration(BaseModel):
    Hardware: Hardware
    Version: Version
    Status: Status
    OTA: OTA
    Permission: Permission


class DnnOtaBody(BaseModel):
    UpdateModule: str = Field(default="DnnModel")
    DesiredVersion: str
    PackageUri: str
    HashValue: str


class DnnOta(BaseModel):
    OTA: DnnOtaBody


class DnnDeleteBody(BaseModel):
    UpdateModule: str = Field(default="DnnModel")
    DeleteNetworkID: str


class DnnDelete(BaseModel):
    OTA: DnnDeleteBody


class SetFactoryReset(BaseModel):
    Permission: Permission
