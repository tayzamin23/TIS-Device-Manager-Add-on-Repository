from pydantic import BaseModel
from typing import List

class Device(BaseModel):
    name: str
    ip: str
    subnet: int
    device_id: int
    type: str

class Appliance(BaseModel):
    name: str
    type: str
    device: str
    channels: dict

class Project(BaseModel):
    devices: List[Device] = []
    appliances: List[Appliance] = []
