from dataclasses import dataclass
from internal.models.vehicle import Vehicle
from internal.models.card import Card

@dataclass
class Account:
    phone:str
    pswd:str
    
    memberId: str | None = None
    vehiclesList: list[Vehicle] | None = None
    cardsList: list[Card] | None = None