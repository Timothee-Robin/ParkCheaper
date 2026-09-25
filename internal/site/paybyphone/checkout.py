from datetime import datetime, timezone
import json
import time
from internal.client.client import Client
from internal.site.paybyphone.parkingZone import ParkingZone
import uuid

class CheckoutClient:

    def __init__(self, client: Client, ticketList: list[int], parkingZone: ParkingZone, licensePlate: str | None = None):
        self.client = client
        self.ticketList = ticketList  # Ex: [30, 60, 60]
        if not self.client.account.vehiclesList:
            raise ValueError("No vehicles found on account. Make sure auth.checkVehicles() was called.")
        if not self.client.account.cardsList:
            raise ValueError("No payment cards found on account. Make sure auth.checkPayment() was called.")
        if licensePlate:
            self.licensePlate = licensePlate
        else:
            self.licensePlate = self.client.account.vehiclesList[0].licensePlate
        self.payment = self.client.account.cardsList[0]
        self.parkingZone = parkingZone
        self.zone = self.parkingZone.zone
        
        
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
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        }



    def checkoutTicket(self, duration_minutes: int) -> dict:
        """Triggers ticket purchase and payment on PayByPhone."""
        print(f"[+] Purchasing ticket for {duration_minutes} min in zone {self.zone} (Plate: {self.licensePlate})...")
        quote = self.createQuoteWithCard(duration_minutes)
        startParking = self.startParking(quote['quoteId'])
        job = self.create3DS(
            parkingSessionId=startParking["parkingSessionId"],
            endingTime=startParking["endingTime"],
            amount=startParking["amount"],
            parkingSegmentId=startParking["parkingSegmentId"]
        )
        status = self.check3DS(jobId=job)
        return {
            "status": status,
            "jobId": job,
            "quote": quote,
            "startParking": startParking
        }



    def checkParkingSession(self) -> dict:
        """Retrieves active session and returns its expireTime in UTC timestamp."""
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
            raise ValueError("No active session detected on API.")

        # Filter session matching our vehicle and zone
        matching_session = None
        for s in sessions:
            zone_match = (
                str(s.get("location", {}).get("advertisedLocationId")) == str(self.zone)
            )
            plate_match = (
                s.get("vehicle", {}).get("licensePlate") == self.licensePlate
            )
            if zone_match and plate_match and s.get("status") == "ACTIVE":
                matching_session = s
                break

        if not matching_session:
            raise ValueError(
                f"No active session for license plate {self.licensePlate} in zone {self.zone}."
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
        
      
      
        
    def createQuoteWithCard(self, duration: int) -> dict:
        if not self.parkingZone.ratePolicyId:
            self.parkingZone.getRestrictionOnZone()

        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
            "operationName": None,
            "variables": {
                "requests": [
                    {
                        "quoteRequestId": str(uuid.uuid4()),
                        "product": "PARKING",
                        "details": {
                            "locationId": str(self.parkingZone.zone),
                            "advertisedLocationId": str(self.parkingZone.zone),
                            "ratePolicyId": str(self.parkingZone.ratePolicyId),
                            "parkingQuoteOperation": "Start",
                            "durationTimeUnit": "Minutes",
                            "durationQuantity": str(duration),
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
        
        r = self.client.post(url, headers=self._get_headers(), payload=payload)
        data = r.json()
        
        if not data or "data" not in data or "createQuotesV1" not in data["data"]:
            raise ValueError(f"Erreur lors de la récupération des devis : {data}")
                
        simplerData = data["data"]["createQuotesV1"]["createQuotesResponse"]
        quoteErrors = simplerData.get("quoteErrors", [])
        if quoteErrors:
            raise ValueError(f"Erreur API devis PayByPhone : {quoteErrors}")

        quotes = simplerData.get("quotes", [])
        if not quotes:
            raise ValueError("Aucun devis disponible pour cette durée.")

        quoteId = quotes[0]["quoteId"]
        price = simplerData["totalCost"]["amount"]
        
        return {"price": price, "quoteId": quoteId}
    
    
    
    def startParking(self, quoteId: str) -> dict:
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
                
        r = self.client.post(url, headers=self._get_headers(), payload=payload)
        data = r.json()
        
        if not data or "data" not in data or "startParkingSessionV1" not in data["data"]:
            raise ValueError(f"Erreur au démarrage du stationnement : {data}")     
        
        simplerData = data['data']['startParkingSessionV1']['parkingSessionResponse']
        
        raw_metadata = simplerData.get('metadata')
        if isinstance(raw_metadata, str):
            try:
                metadata = json.loads(raw_metadata)
            except Exception:
                metadata = {}
        elif isinstance(raw_metadata, dict):
            metadata = raw_metadata
        else:
            metadata = {}

        parkingSegmentId = str(metadata.get('parkingSegmentId', raw_metadata or ''))
        parkingSessionId = simplerData['parkingSessionId']
        amount = simplerData["segmentTotalCost"]["amount"]
        endingTime = simplerData["expireTime"]
        
        return {
            'parkingSessionId': parkingSessionId,
            'parkingSegmentId': parkingSegmentId,
            'amount': amount,
            'endingTime': endingTime
        }
    
    
    
    def create3DS(self, parkingSessionId: str, endingTime: str, amount: float, parkingSegmentId: str) -> str:
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
                                    "value": float(amount),
                                    "isoCurrencyCode": "EUR"
                                },
                                "required": True,
                                "metadata": json.dumps({"parkingSegmentId": str(parkingSegmentId)})
                            }
                        ]
                    }
                }
            },
            "query": "mutation CreateJobV1($input: CreateJobV1Input!) {\n  createJobV1(input: $input) {\n    createJobResponse {\n      jobId\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        })
        
        r = self.client.post(url, headers=self._get_headers(), payload=payload)
        data = r.json()
        
        if not data or "data" not in data or "createJobV1" not in data["data"]:
            raise ValueError(f"Error creating 3DS payment job: {data}")
        
        jobId = data['data']['createJobV1']['createJobResponse']['jobId']
        return jobId
    
    
    
    def check3DS(self, jobId: str, max_retries: int = 30, delay: float = 1.0) -> str:
        url = "https://consumer.paybyphoneapis.com/uapi/graphql"

        payload = json.dumps({
            "operationName": None,
            "variables": {
                "jobId": jobId
            },
            "query": "query GetJobV1($jobId: UUID!) {\n  getJobV1(jobId: $jobId) {\n    jobId\n    status\n    captureGroups {\n      captureGroupId\n      stage\n      status\n      closedAt\n      authentication {\n        hiddenIframe\n        challengeUrl\n        challengeHtml\n        token\n        __typename\n      }\n      lineItems {\n        itemId\n        productReferenceId\n        status\n        metadata\n        amount {\n          value\n          isoCurrencyCode\n          __typename\n        }\n        executionDetails {\n          isFailure\n          code\n          message\n          metadata\n          __typename\n        }\n        __typename\n      }\n      couponAmount {\n        value\n        isoCurrencyCode\n        __typename\n      }\n      couponDetails {\n        status {\n          code\n          status\n          message\n          __typename\n        }\n        couponId\n        redeemedAt\n        requestedAt\n        totalAmountRedeemed {\n          value\n          isoCurrencyCode\n          __typename\n        }\n        __typename\n      }\n      executionDetails {\n        isFailure\n        code\n        message\n        metadata\n        captureGroupStage\n        __typename\n      }\n      isPaymentOpenToModification\n      __typename\n    }\n    executionDetails {\n      isFailure\n      code\n      message\n      metadata\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
        })

        for attempt in range(max_retries):
            r = self.client.post(url, headers=self._get_headers(), payload=payload)
            data = r.json()
            if not data or "data" not in data or "getJobV1" not in data["data"]:
                raise ValueError(f"Error checking 3DS: {data}")
            
            capture_groups = data["data"]["getJobV1"].get("captureGroups", [])
            if not capture_groups or not capture_groups[0].get("lineItems"):
                time.sleep(delay)
                continue

            line_item = capture_groups[0]["lineItems"][0]
            status = line_item.get("status")

            print(f"[*] 3DS Status: {status} (attempt {attempt + 1}/{max_retries})")

            if status == "pending":
                time.sleep(delay)
                continue
            elif status == "fulfillmentCompleted":
                return status
            else:
                exec_details = line_item.get("executionDetails")
                raise ValueError(f"Unexpected or failed 3DS status: {status} - Details: {exec_details}")

        raise TimeoutError(f"3DS verification timed out after {max_retries} attempts.")
        

             

                    