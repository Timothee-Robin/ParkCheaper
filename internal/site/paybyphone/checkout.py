from datetime import datetime, timezone
import json
import time
from internal.client.client import Client
from internal.site.paybyphone.parkingZone import ParkingZone
import uuid

class CheckoutClient:

    def __init__(self, client: Client, ticketList: list[int], parkingZone: ParkingZone):
        self.client = client
        self.ticketList = ticketList  # Ex: [30, 60, 60]
        self.licensePlate = self.client.account.vehiclesList[0].licensePlate
        self.payment = self.client.account.cardsList[0]
        self.parkingZone = parkingZone
        
        
    def _get_headers(self) -> dict:
        return {
            "accept": "*/*",
            "accept-language": "fr-FR,fr;q=0.7",
            "authorization": f"Bearer {self.client.accessToken}",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": "https://m.paybyphone.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://m.paybyphone.com/",
            "sec-ch-ua": '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "sec-gpc": "1",
        }

    def checkoutTicket(self, duration_minutes: int) -> dict:
        """Déclenche la mutation d'achat/paiement réel du ticket sur PayByPhone."""
        # TODO: Remplir avec la mutation GraphQL de paiement réel (ex: CompletePaymentSession / StartParkingSession)
        print(
            f"[+] Achat en cours pour {duration_minutes} min sur zone {self.parkingZone.zone}..."
        )
        return {}

    def checkParkingSession(self) -> dict:
        """Récupère la session active et renvoie son expireTime en timestamp UTC."""
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps(
            {
                "operationName": None,
                "variables": {
                    "input": {
                        "periodType": "CURRENT",
                        "productTypes": "ParkingSession, Reservation, Autopay",
                        "offset": 0,
                        "limit": 10,
                    }
                },
                "query": """query GetParkingSessionsWithAccessCodeV1($input: GetParkingSessionsInput!) {
                getParkingSessionsV1(input: $input) {
                    parkingSessionId
                    status
                    expireTime
                    location {
                        advertisedLocationId
                    }
                    vehicle {
                        licensePlate
                    }
                }
            }""",
            }
        )

        r = self.client.post(url, headers=self._get_headers(), payload=payload)
        data = r.json()

        sessions = data.get("data", {}).get("getParkingSessionsV1", [])
        if not sessions:
            raise ValueError("Aucune session active détectée sur l'API.")

        # Filtrer la session correspondant à notre véhicule et zone
        matching_session = None
        for s in sessions:
            zone_match = (
                s.get("location", {}).get("advertisedLocationId") == self.zone
            )
            plate_match = (
                s.get("vehicle", {}).get("licensePlate") == self.licensePlate
            )
            if zone_match and plate_match and s.get("status") == "ACTIVE":
                matching_session = s
                break

        if not matching_session:
            raise ValueError(
                f"Aucune session active pour la plaque {self.licensePlate} en zone {self.zone}."
            )

        # Parse ISO date '2026-09-19T10:12:24.000Z'
        expire_str = matching_session["expireTime"].replace("Z", "+00:00")
        expire_dt = datetime.fromisoformat(expire_str)

        return {
            "session_id": matching_session["parkingSessionId"],
            "expire_dt": expire_dt,
            "seconds_left": (
                expire_dt - datetime.now(timezone.utc)
            ).total_seconds(),
        }

    def scheduleTickets(self) -> None:
        """Ordonnance et enchaîne séquentiellement la liste de tickets."""
        total = len(self.ticketList)

        for idx, duration in enumerate(self.ticketList, start=1):
            print(f"\n--- Ticket {idx}/{total} : {duration} minutes ---")

            # 1. Paiement du ticket
            self.checkoutTicket(duration)

            # 2. Laisser 3 secondes à l'API pour inscrire la session
            time.sleep(3)

            # 3. Vérification de la session active
            session = self.checkParkingSession()
            seconds_remaining = session["seconds_left"]

            print(
                f"[OK] Session confirmée. Expire à : {session['expire_dt'].strftime('%H:%M:%S')} UTC"
            )

            # Si ce n'est pas le dernier ticket, on attend la fin pour enchaîner
            if idx < total:
                # On ajoute une marge de 3 secondes pour s'assurer que le ticket est bien expiré côté serveur
                sleep_duration = max(0.0, seconds_remaining + 3.0)
                print(
                    f"[*] Attente de {int(sleep_duration // 60)}m {int(sleep_duration % 60)}s avant le prochain ticket..."
                )
                time.sleep(sleep_duration)

        print("\n[+] Tous les tickets programmés ont été consommés avec succès.")
        
        
    def createQuoteWithCard(self,duration):
        
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
        "operationName": None,
        "variables": {
            "requests": [
            {
                "quoteRequestId": str(uuid.uuid4()),
                "product": "PARKING",
                "details": {
                "locationId": self.parkingZone.zone,
                "advertisedLocationId": self.parkingZone.zone,
                "ratePolicyId": self.parkingZone.ratePolicyId,
                "parkingQuoteOperation": "Start",
                "durationTimeUnit": "Minutes",
                "durationQuantity": duration,
                "licensePlate": self.licensePlate,
                "stall": "",
                "paymentAccountId": self.payment.paymentAccountId,
                "paymentCardType": self.payment.cardType,
                "paymentScope": "Private"
                }
            }
            ]
        },
        "query": "mutation CreateQuotesV1($requests: [QuoteRequestInput!]!) {\n  createQuotesV1(input: {requests: $requests}) {\n    createQuotesResponse {\n      totalCost {\n        amount\n        currency\n        __typename\n      }\n      quotes {\n        quoteId\n        quoteRequestId\n        cost {\n          amount\n          currency\n          __typename\n        }\n        details {\n          quoteId\n          locationId\n          stall\n          quoteDate\n          parkingStartTime\n          parkingExpiryTime\n          parkingDurationAdjustment\n          licensePlate\n          corporateAccountSmsOverride\n          corporateAccountSmsConfirmationOverride\n          corporateAccountSmsReminderOverride\n          promotionApplied {\n            id\n            cost {\n              amount\n              currency\n              __typename\n            }\n            duration {\n              quantity\n              timeUnit\n              __typename\n            }\n            displayName\n            usage\n            isSelectedByUser\n            isTimeSplit\n            isExternal\n            configuredDuration {\n              quantity\n              timeUnit\n              __typename\n            }\n            minimumIncrement {\n              quantity\n              timeUnit\n              __typename\n            }\n            __typename\n          }\n          totalCost {\n            amount\n            currency\n            __typename\n          }\n          quoteItems {\n            quoteItemType\n            name\n            costAmount {\n              amount\n              currency\n              __typename\n            }\n            subQuoteItems {\n              quoteItemType\n              name\n              costAmount {\n                amount\n                currency\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        product\n        __typename\n      }\n      quoteErrors {\n        quoteRequestId\n        product\n        status\n        reason\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
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
            'sec-gpc': '1',
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        
        data = r.json()
        
        if not data or not "data" in data or not "createQuotesV1" in data["data"]:
            raise(ValueError("Error getting Quotes"))
                
        simplerData = data["data"]["createQuotesV1"]["createQuotesResponse"]
        quoteId = simplerData["quotes"][0]["quoteId"]
        price = simplerData["totalCost"]["amount"]
        
        return {"price":price,"quoteId":quoteId}
    
    def startParking(self,quoteId):
        
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
        "operationName": None,
        "variables": {
            "input": {
            "request": {
                "quoteId": quoteId
            }
            }
        },
        "query": "mutation StartParkingSessionV1($input: StartParkingSessionV1Input!) {\n  startParkingSessionV1(input: $input) {\n    parkingSessionResponse {\n      parkingSessionId\n      expireTime\n      isEarlyCapture\n      segmentTotalCost {\n        amount\n        currency\n        __typename\n      }\n      metadata\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
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
        'sec-gpc': '1',
        }
                
        r = self.client.post(url,headers=headers,payload=payload)
        data = r.json()
        
        if not data or not "data" in data or not "startParkingSessionV1" in data["data"]:
            raise(ValueError("Error Starting Parking"))     
        
        simplerData = data['data']['startParkingSessionV1']['parkingSessionResponse']
        
        parkingSegmentId = simplerData['metadata']['parkingSegmentId']
        parkingSessionId = simplerData['parkingSessionId']
        
        return {'parkingSessionId':parkingSessionId,'parkingSegmentId':parkingSegmentId}
    
    def create3DS(self,parkingSessionId,endingTime,amount,parkingSegmentId):
        
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
        "operationName": None,
        "variables": {
            "input": {
            "request": {
                "paymentMethod": {
                "paymentMethodType": "PaymentAccount",
                "paymentDetails": {
                    "$type": "paymentAccount",
                    "paymentAccountId": self.payment.paymentAccountId,
                    "cvv": None,
                    "clientBrowserDetails": {
                    "browserAcceptHeader": "text/html",
                    "browserColorDepth": 24,
                    "browserJavaEnabled": False,
                    "browserLanguage": "fr-FR",
                    "browserScreenHeight": 1440,
                    "browserScreenWidth": 2560,
                    "browserTimeZone": 120,
                    "browserUserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                    "flag3D": "Y",
                    "httpAccept": "*/*",
                    "httpUserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
                    }
                }
                },
                "lineItems": [
                {
                    "productType": "parking",
                    "productReferenceId": parkingSessionId,
                    "vendorId": "12021",
                    "endingTime": endingTime,
                    "isEarlyCapture": False,
                    "amount": {
                    "value": amount,
                    "isoCurrencyCode": "EUR"
                    },
                    "required": True,
                    "metadata": '{"parkingSegmentId":"' + parkingSegmentId + '"}'
                }
                ]
            }
            }
        },
        "query": "mutation CreateJobV1($input: CreateJobV1Input!) {\n  createJobV1(input: $input) {\n    createJobResponse {\n      jobId\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        })
        headers = {
        'accept': '*/*',
        'accept-language': 'fr-FR,fr;q=0.9',
        'authorization': 'Bearer eyJ4NXQiOiJTcEE0cFc1U0RXZ09STW1FbXRTczkwX1VVZWciLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjRBOTAzOEE1NkU1MjBENjgwRTQ0Qzk4NDlBRDRBQ0Y3NEZENDUxRTgifQ.eyJtZW1iZXJpZCI6ImJkMTQ3Y2ZkLWEzZDUtNDVkMi05YjA4LTM1YmFkMjVkYjVmMCIsImFjdGl2ZXVzZXJhY2NvdW50IjoiYmQxNDdjZmQtYTNkNS00NWQyLTliMDgtMzViYWQyNWRiNWYwIiwibmJmIjoxNzg5OTczNzYyLCJndHkiOiJwYXNzd29yZCIsImp0aSI6IlZxVTJ4aWMxc1M1SjU5ZVplQUhwSyIsInN1YiI6ImJkMTQ3Y2ZkLWEzZDUtNDVkMi05YjA4LTM1YmFkMjVkYjVmMCIsImlhdCI6MTc4OTk3Mzc2MiwiZXhwIjoxNzg5OTc0OTYyLCJzY29wZSI6InBheWJ5cGhvbmUiLCJpc3MiOiJQYXlCeVBob25lIElkZW50aXR5IEFuZCBBY2Nlc3MiLCJhdWQiOlsiaHR0cHM6Ly9jb25zdW1lci5wYXlieXBob25lYXBpcy5jb20iLCJodHRwczovL2NvbnN1bWVyLnBheWJ5cGhvbmVhcGlzLmNvbS9pZGVudGl0eSIsInBicF9hcGlfZnBzcGF5bWVudHMiLCJwYnBfYXBpX3BhcmtpbmciLCJwYnBfYXBpX3BheW1lbnQiLCJwYnBfYXBpX3Byb2ZpbGVzZXJ2aWNlIiwicGJwX2lkYSIsImh0dHA6Ly9hcGkucGF5YnlwaG9uZS5jb20iLCJodHRwOi8vYXBpLnFhLnBheWJ5cGhvbmUuY29tIl0sImF6cCI6InBheWJ5cGhvbmVfd2ViIn0.i7cX-gmJoDLqkMyWJAMl-NLkPxShCTiQ6HNDBLLfkZ_D1x2kXMg8_nkUafo3VqQMmGmDER6nJwYU4pSyjLv1kZHudVbKAQr9GN0pMtiKfx3dtxRyof9FArlL7MfKPkH8tzukYVivVRzW9LJQ3ST54RZWHtPypwrryMflyfsMP-pYG03yVLof_1Jldt4YdjSAOMH9VWdu9crU-LHhIgaSSNg50iDkFsClGs3V3Zfc22oU86zLwgHDfXtBClBzu6yBvCzCIYTzmU94nfTlzaRndteyKjKnTJTSHqq-PCPxsH9mTseUY0ezILglCzeRx3pzC0a8udO7es2IVPe-DLObDA',
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
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
        }
        
        r = self.client.post(url,headers=headers,payload=payload)
        data = r.json()
        
        if not data or not "data" in data or not "createJobV1" in data["data"]:
            raise(ValueError("Error checkout"))
        
        jobId = data['data']['createJobV1']['createJobResponse']['jobId']
        
        return jobId
    
    
    def check3DS(self,jobId):
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
        "operationName": None,
        "variables": {
            "jobId": jobId
        },
        "query": "query GetJobV1($jobId: UUID!) {\n  getJobV1(jobId: $jobId) {\n    jobId\n    status\n    captureGroups {\n      captureGroupId\n      stage\n      status\n      closedAt\n      authentication {\n        hiddenIframe\n        challengeUrl\n        challengeHtml\n        token\n        __typename\n      }\n      lineItems {\n        itemId\n        productReferenceId\n        status\n        metadata\n        amount {\n          value\n          isoCurrencyCode\n          __typename\n        }\n        executionDetails {\n          isFailure\n          code\n          message\n          metadata\n          __typename\n        }\n        __typename\n      }\n      couponAmount {\n        value\n        isoCurrencyCode\n        __typename\n      }\n      couponDetails {\n        status {\n          code\n          status\n          message\n          __typename\n        }\n        couponId\n        redeemedAt\n        requestedAt\n        totalAmountRedeemed {\n          value\n          isoCurrencyCode\n          __typename\n        }\n        __typename\n      }\n      executionDetails {\n        isFailure\n        code\n        message\n        metadata\n        captureGroupStage\n        __typename\n      }\n      isPaymentOpenToModification\n      __typename\n    }\n    executionDetails {\n      isFailure\n      code\n      message\n      metadata\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
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
        if not data or not "data" in data or not "getJobV1" in data["data"]:
            raise(ValueError("Error checking 3DS"))
        
             
             

                    