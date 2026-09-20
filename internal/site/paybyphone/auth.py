from internal.client.client import Client
from internal.models.vehicle import Vehicle
from internal.models.account import Account
from internal.models.card import Card

import json



class AuthServices():
    def __init__(self,client:Client):
        self.client = client

    def login(self):
        url = "https://auth.paybyphoneapis.com/consumer/token"
        
        payload = f'grant_type=password&client_id=paybyphone_web&username=%2B{self.client.account.phone}&password={self.client.account.pswd}'
        
        headers = {
            'accept': '*/*',
            'accept-language': 'fr-FR,fr;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://m.paybyphone.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://m.paybyphone.com/',
            'sec-ch-ua': '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1',
            'x-pbp-clienttype': 'WebApp'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        
        data = r.json()
        
        if data and "access_token" in data:
            self.client.accessToken = data["access_token"]
            self.client.refreshToken = data["refresh_token"]
        
        elif data and "error" in data:
           raise ValueError(f"Error : {data["error_description"]}") 
        
        else:
            raise ValueError("Error login in")
        
    def checkAccountdetails(self):
        
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"
        
        payload = json.dumps({
            "operationName": None,
            "variables": {},
            "query": "query GetUserAccountV1 {\n  getUserAccountV1 {\n    memberId\n    type\n    status\n    phone {\n      number\n      status\n      isUsername\n      country\n      countryCode\n      nationalNumber\n      operator\n      __typename\n    }\n    email {\n      address\n      status\n      __typename\n    }\n    country\n    language\n    address {\n      street\n      city\n      provinceState\n      postalCode\n      country\n      __typename\n    }\n    name {\n      firstName\n      lastName\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        })
        
        headers = {
            'accept': '*/*',
            'accept-language': 'fr-FR,fr;q=0.8',
            'authorization': f'Bearer {self.client.accessToken}',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://m.paybyphone.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://m.paybyphone.com/',
            'sec-ch-ua': '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        data = r.json()
        
        if not data or not "data" in data or not "getUserAccountV1" in data["data"]:
            raise(ValueError("Error getting account details"))
        
        simplerData = data["data"]["getUserAccountV1"]
        
        accDetails = {
            "phone":simplerData["phone"]["number"],
            "email":simplerData["email"]["address"],
            "country":simplerData["country"],
            "memberId":simplerData['memberId']
        }
        
        print("Account details : \n",accDetails)
        
        self.client.account.memberId = simplerData["memberId"]
        
        
    def checkVehicles(self):
            
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"
        
        payload = json.dumps(
           {"operationName":None,"variables":{"input":{"profileName":"PayByPhone"}},"query":"query GetVehiclesV3($input: GetVehiclesInput!) {\n  getVehiclesV3(input: $input) {\n    vehicleId\n    legacyVehicleId\n    licensePlate\n    country\n    jurisdiction\n    type\n    attributes\n    archived\n    profile {\n      photo\n      description\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"}
        )
        
        headers = {
            'accept': '*/*',
            'accept-language': 'fr-FR,fr;q=0.8',
            'authorization': f'Bearer {self.client.accessToken}',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://m.paybyphone.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://m.paybyphone.com/',
            'sec-ch-ua': '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        data = r.json()
        
        if not data or not "data" in data or not "getVehiclesV3" in data["data"] or len(data["data"]["getVehiclesV3"])==0:
            raise(ValueError("Error getting vehicles details make sure your vehicles are registered"))
        
        simplerData = data["data"]["getVehiclesV3"]
        
        vehicles = []
        
        for vehicle in simplerData:
            newVehicle = Vehicle(vehicle['type'],vehicle['licensePlate'],vehicle['vehicleId'])
            
            vehicles.append(newVehicle)
            
        self.client.account.vehiclesList = vehicles
        
        print(self.client.account.vehiclesList)
        
        
    def checkPayement(self):
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
        "operationName": None,
        "variables": {
            "input": {
            "mandateCountryCode": "FR"
            }
        },
        "query": "query GetPaymentAccountsV1($input: GetPaymentAccountsInput!) {\n  getPaymentAccountsV1(input: $input) {\n    paymentCards {\n      cardType\n      maskedCardNumber\n      accountType\n      paymentAccountId\n      paymentScope\n      corporateClientId\n      expiryMonth\n      expiryYear\n      __typename\n    }\n    mno {\n      status\n      operator\n      phoneNumber\n      paymentAccountId\n      paymentScope\n      corporateClientId\n      expiryMonth\n      expiryYear\n      __typename\n    }\n    twintAccounts {\n      accountType\n      paymentAccountId\n      paymentScope\n      mandates {\n        id\n        status\n        __typename\n      }\n      __typename\n    }\n    paypalAccounts {\n      accountType\n      paymentAccountId\n      paymentScope\n      mandates {\n        id\n        status\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        })
        headers = {
        'accept': '*/*',
        'accept-language': 'fr-FR,fr;q=0.9',
        'authorization': f'Bearer {self.client.accessToken}',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://m.paybyphone.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://m.paybyphone.com/',
        'sec-ch-ua': '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'sec-gpc': '1'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        data = r.json()
            
        if not data or not "data" in data or not "getPaymentAccountsV1" in data["data"] or len(data["data"]["getPaymentAccountsV1"])==0:
            raise(ValueError("Error getting payements details make sure your cards are registered"))
        
        simplerData = data["data"]["getPaymentAccountsV1"]
        
        cards = []
        
        for card in simplerData["paymentCards"]:
            newCard = Card(card['maskedCardNumber'],card['cardType'],card['paymentAccountId'])
            
            cards.append(newCard)
            
        self.client.account.cardsList = cards
        
        print(self.client.account.cardsList)