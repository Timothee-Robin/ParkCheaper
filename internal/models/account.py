from dataclasses import dataclass
from internal.models.vehicle import Vehicle
@dataclass
class Account:
    phone:str
    pswd:str
    
    memberId: str | None = None
    vehiclesList: list[Vehicle] | None = None
    