import sys
import os
from dotenv import load_dotenv

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from internal.models.account import Account
from internal.client.client import Client
from internal.site.paybyphone.auth import AuthServices
from internal.site.paybyphone.parkingZone import ParkingZone
from internal.site.paybyphone.parkingOptimizer import ParkingOptimizer

if __name__ == "__main__":
    load_dotenv()
    account = Account(os.getenv('phone'), os.getenv('pswd'))
    client = Client()
    client.setAccount(account)
    
    auth = AuthServices(client)
    auth.login()
    auth.checkAccountdetails()
    auth.checkVehicles()
    
     
    parkingZone = ParkingZone(client,'94802')
    parkingOptimizer = ParkingOptimizer(step_minutes=15,parkingZone=parkingZone)
    
    parkingOptimizer.fetch_tariffs()
    print(parkingOptimizer.optimize("14:00", "17:30"))