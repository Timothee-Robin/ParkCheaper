from datetime import datetime, timezone
import json
import time
from internal.client.client import Client


class CheckoutClient:

    def __init__(self, client: Client, ticketList: list[int], zone: str):
        self.client = client
        self.ticketList = ticketList  # Ex: [30, 60, 60]
        self.zone = str(zone)
        self.licensePlate = self.client.account.vehiclesList[0].licensePlate

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
            f"[+] Achat en cours pour {duration_minutes} min sur zone {self.zone}..."
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