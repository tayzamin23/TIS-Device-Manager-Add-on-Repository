from pydantic import BaseModel
from typing import List, Optional

class Device(BaseModel):
    ip: str
    port: int = 6000
    name: Optional[str] = None
    subnet_id: Optional[int] = None
    device_id: Optional[int] = None


class Appliance(BaseModel):
    id: str
    name: str
    device_ip: str
    device_port: int = 6000
    type: str  # switch, dimmer, shutter, sensor, etc.
    channel: int
    metadata: Optional[dict] = {}


class Project(BaseModel):
    name: str
    devices: List[Device] = []
    appliances: List[Appliance] = []
