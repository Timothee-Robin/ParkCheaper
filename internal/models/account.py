from dataclasses import dataclass
from internal.models.vehicle import Vehicle
from internal.models.card import Card

@dataclass
class Account:
    phone:str
    pswd:str
    email: str | None = None

    memberId: str | None = None
    vehiclesList: list[Vehicle] | None = None
    cardsList: list[Card] | None = None