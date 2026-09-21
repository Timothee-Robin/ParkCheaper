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
from internal.site.paybyphone.checkout import CheckoutClient

if __name__ == "__main__":
    load_dotenv()
    
    phone = os.getenv('phone')
    pswd = os.getenv('pswd')
    if not phone or not pswd:
        raise ValueError("Veuillez définir 'phone' et 'pswd' dans le fichier .env")

    account = Account(phone, pswd)
    client = Client()
    client.setAccount(account)
    
    print("[*] Connexion et récupération du profil...")
    auth = AuthServices(client)
    auth.login()
    auth.checkAccountdetails()
    auth.checkVehicles()
    auth.checkPayement()
    
    # 1. Sélection de la zone de stationnement
    zone_id = "94802"
    parkingZone = ParkingZone(client, zone_id)
    
    # 2. Préparation du Checkout
    # ticketList: liste des durées de tickets en minutes à acheter
    ticketList = [15]
    checkout = CheckoutClient(client=client, ticketList=ticketList, parkingZone=parkingZone)

    print("\n" + "=" * 50)
    print("PARAMÈTRES DU CHECKOUT")
    print("=" * 50)
    print(f"Zone           : {checkout.zone}")
    print(f"Véhicule       : {checkout.licensePlate}")
    print(f"Carte bancaire : {checkout.payment.maskedCardNumber} ({checkout.payment.cardType})")
    print(f"Tickets prévus : {checkout.ticketList} min")
    print("=" * 50 + "\n")

    # 3. Test du checkout
    # Option 1 : Achat direct d'un seul ticket de test (ex: premier de la liste)
    duration_to_test = ticketList[0]
    print(f"[*] Démarrage du test de checkout pour un ticket de {duration_to_test} minutes...")
    result = checkout.checkoutTicket(duration_to_test)
    print("[+] Résultat du checkout :", result)

    # Option 2 : Pour lancer l'enchaînement automatique de toute la liste :
    # checkout.scheduleTickets()