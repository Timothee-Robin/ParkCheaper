import json
import uuid
from datetime import datetime
from internal.client.client import Client


class ParkingZone:

    def __init__(self, client: Client, zone: str, licensePlate: str | None = None):
        self.zone = str(zone)
        self.client = client
        self.ratePolicyId: str | None = None
        self.maxStay: int = 0
        if licensePlate:
            self.licensePlate = licensePlate
        elif self.client.account and self.client.account.vehiclesList:
            self.licensePlate = self.client.account.vehiclesList[0].licensePlate
        else:
            self.licensePlate = ""
        self._url = "https://consumer.paybyphoneapis.com/uapi/graphql"

    def _get_headers(self) -> dict:
        return {
            "accept": "*/*",
            "accept-language": "fr-FR,fr;q=0.5",
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

    def getRestrictionOnZone(self) -> None:
        payload = json.dumps(
            {
                "operationName": None,
                "variables": {
                    "input": {
                        "locationId": self.zone,
                        "licensePlate": self.licensePlate,
                    }
                },
                "query": """query GetRateOptionsV1($input: GetRateOptionsInput!) {
                    getRateOptionsV1(input: $input) {
                        ratePolicyId
                        effectiveMaxStayDuration {
                            quantity
                            timeUnit
                        }
                    }
                }""",
            }
        )

        r = self.client.post(
            self._url, headers=self._get_headers(), payload=payload
        )
        data = r.json()

        if not data or "data" not in data or "getRateOptionsV1" not in data["data"]:
            raise ValueError("Impossible de récupérer les restrictions de la zone")

        rate_options = data["data"]["getRateOptionsV1"][0]
        
        self.ratePolicyId = rate_options["ratePolicyId"]
        stay_info = rate_options.get("effectiveMaxStayDuration", {})
        qty = int(stay_info.get("quantity", 0))
        unit = stay_info.get("timeUnit", "Minutes")

        if unit == "Days":
            self.maxStay = qty * 24 * 60
        elif unit == "Hours":
            self.maxStay = qty * 60
        else:
            self.maxStay = qty

        if self.maxStay <= 0:
            self.maxStay = 240

    def getQuote(self, duration_minutes: int) -> tuple[int, float, int, str | None]:
        """Retourne un tuple : (durée_totale_min, coût_total, durée_offerte_min, usage_promo)"""
        if not self.ratePolicyId:
            self.getRestrictionOnZone()

        payload = json.dumps(
            {
                "operationName": None,
                "variables": {
                    "requests": [
                        {
                            "quoteRequestId": str(uuid.uuid4()),
                            "product": "PARKING",
                            "details": {
                                "locationId": self.zone,
                                "advertisedLocationId": self.zone,
                                "ratePolicyId": self.ratePolicyId,
                                "parkingQuoteOperation": "Start",
                                "durationTimeUnit": "Minutes",
                                "durationQuantity": str(duration_minutes),
                                "licensePlate": self.licensePlate,
                                "stall": "",
                                "paymentAccountId": "",
                                "paymentCardType": "",
                                "paymentScope": "",
                            },
                        }
                    ]
                },
                "query": """mutation CreateQuotesV1($requests: [QuoteRequestInput!]!) {
                    createQuotesV1(input: {requests: $requests}) {
                        createQuotesResponse {
                            totalCost {
                                amount
                                currency
                            }
                            quotes {
                                details {
                                    parkingStartTime
                                    parkingExpiryTime
                                    parkingDurationAdjustment
                                    promotionApplied {
                                        cost {
                                            amount
                                        }
                                        duration {
                                            quantity
                                            timeUnit
                                        }
                                        usage
                                    }
                                }
                            }
                            quoteErrors {
                                reason
                                status
                            }
                        }
                    }
                }""",
            }
        )

        r = self.client.post(
            self._url, headers=self._get_headers(), payload=payload
        )
        data = r.json()

        response_root = (
            data.get("data", {})
            .get("createQuotesV1", {})
            .get("createQuotesResponse", {})
        )
        errors = response_root.get("quoteErrors", [])
        if errors:
            raise ValueError(f"Erreur API PayByPhone: {errors}")

        quotes = response_root.get("quotes", [])
        if not quotes:
            raise ValueError("Aucun devis disponible pour cette durée.")

        details = quotes[0]["details"]
        total_cost = float(response_root["totalCost"]["amount"])

        # Calcul de la durée exacte allouée par le serveur (durée demandée)
        t_start = datetime.fromisoformat(
            details["parkingStartTime"].replace("Z", "+00:00")
        )
        t_end = datetime.fromisoformat(
            details["parkingExpiryTime"].replace("Z", "+00:00")
        )

        # Détection précise du quota gratuit
        promo = details.get("promotionApplied")
        promo_duration = 0
        promo_usage = None

        if promo and promo.get("cost", {}).get("amount") == 0.0:
            dur_data = promo.get("duration", {})
            if dur_data.get("timeUnit") == "Minutes":
                promo_duration = int(dur_data.get("quantity", 0))
                promo_usage = promo.get("usage")

        # La durée de tarification est la durée demandée (duration_minutes)
        # Note : (t_end - t_start) inclut les plages de gratuité (nuit, pause déjeuner)
        return duration_minutes, total_cost, promo_duration, promo_usage