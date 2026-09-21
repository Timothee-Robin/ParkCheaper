from dataclasses import dataclass

@dataclass
class Vehicle():
    type: str
    licensePlate: str
    vehiculeId: str
    
    @property
    def vehicleId(self) -> str:
        return self.vehiculeId