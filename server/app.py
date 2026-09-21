from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from internal.client.client import Client
from internal.site.paybyphone.auth import AuthServices
from internal.site.paybyphone.parkingZone import ParkingZone
from internal.site.paybyphone.parkingOptimizer import ParkingOptimizer
from internal.site.paybyphone.checkout import CheckoutClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

