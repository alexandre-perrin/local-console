"""
Edge Cloud IF v1 schemas. Properties not included here are ignored. For example, PQ settings.
"""
from pydantic import BaseModel


class Hardware(BaseModel):
    Sensor: str
    SensorId: str
    KG: str
    ApplicationProcessor: str
    LedOn: bool


class Version(BaseModel):
    SensorFwVersion: str
    SensorLoaderVersion: str
    DnnModelVersion: list[str]
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
