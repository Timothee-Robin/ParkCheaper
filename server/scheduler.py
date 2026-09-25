import threading
import time
from datetime import datetime, timezone
from typing import Callable, Any
from internal.site.paybyphone.checkout import CheckoutClient


class ParkingScheduler:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        
        self.status: str = "IDLE"  # IDLE, RUNNING, WAITING_NEXT_TICKET, COMPLETED, STOPPED, ERROR
        self.current_ticket_index: int = 0
        self.total_tickets: int = 0
        self.current_duration: int = 0
        self.seconds_remaining: float = 0.0
        self.next_ticket_at: str | None = None
        self.last_error: str | None = None
        self.history: list[dict[str, Any]] = []
        
        # Listeners for real-time log events (e.g. WebSockets)
        self._log_listeners: list[Callable[[dict[str, Any]], None]] = []

    def add_log_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._log_listeners.append(callback)

    def remove_log_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        if callback in self._log_listeners:
            self._log_listeners.remove(callback)

    def _emit_log(self, message: str, level: str = "INFO", data: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "status": self.status,
            "data": data or {}
        }
        for listener in list(self._log_listeners):
            try:
                listener(event)
            except Exception:
                pass

    def start(self, checkout_client: CheckoutClient) -> None:
        if self.status == "RUNNING" or self.status == "WAITING_NEXT_TICKET":
            raise ValueError("Scheduler is already running.")

        if not checkout_client.ticketList:
            raise ValueError("Ticket list is empty.")

        self._stop_event.clear()
        self.status = "RUNNING"
        self.current_ticket_index = 0
        self.total_tickets = len(checkout_client.ticketList)
        self.current_duration = 0
        self.seconds_remaining = 0.0
        self.next_ticket_at = None
        self.last_error = None
        self.history = []

        self._emit_log(
            f"Scheduler started for {self.total_tickets} ticket(s) in zone {checkout_client.zone} (Plate: {checkout_client.licensePlate})...",
            level="INFO",
            data={"tickets": checkout_client.ticketList, "zone": checkout_client.zone, "licensePlate": checkout_client.licensePlate}
        )

        self._thread = threading.Thread(
            target=self._run,
            args=(checkout_client,),
            name="PayByPhoneSchedulerThread",
            daemon=True
        )
        self._thread.start()

    def stop(self) -> dict[str, str]:
        if self.status in ("RUNNING", "WAITING_NEXT_TICKET"):
            self._stop_event.set()
            self.status = "STOPPED"
            self._emit_log("Scheduler stop requested by user.", level="WARN")
            return {"status": "STOPPED", "message": "Scheduler successfully stopped."}
        return {"status": self.status, "message": "Scheduler was not running."}

    def get_state(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "currentTicketIndex": self.current_ticket_index,
            "totalTickets": self.total_tickets,
            "currentDuration": self.current_duration,
            "secondsRemaining": max(0.0, round(self.seconds_remaining, 1)),
            "nextTicketAt": self.next_ticket_at,
            "lastError": self.last_error,
            "history": self.history
        }

    def _run(self, checkout_client: CheckoutClient) -> None:
        try:
            total = len(checkout_client.ticketList)

            for idx, duration in enumerate(checkout_client.ticketList, start=1):
                if self._stop_event.is_set():
                    self.status = "STOPPED"
                    self._emit_log("Scheduler stopped before purchasing next ticket.", level="WARN")
                    return

                self.current_ticket_index = idx
                self.current_duration = duration
                self.status = "RUNNING"
                
                self._emit_log(
                    f"Purchasing ticket {idx}/{total} : {duration} minutes (Plate: {checkout_client.licensePlate})...",
                    level="INFO",
                    data={"ticketIndex": idx, "duration": duration, "licensePlate": checkout_client.licensePlate}
                )

                # 1. Purchase ticket
                result = checkout_client.checkoutTicket(duration)
                
                ticket_record = {
                    "ticketIndex": idx,
                    "duration": duration,
                    "boughtAt": datetime.now(timezone.utc).isoformat(),
                    "status": result.get("status"),
                    "jobId": result.get("jobId"),
                    "cost": result.get("quote", {}).get("price", 0.0),
                    "licensePlate": checkout_client.licensePlate
                }
                self.history.append(ticket_record)

                self._emit_log(
                    f"Ticket {idx}/{total} confirmed (3DS: {result.get('status')}).",
                    level="SUCCESS",
                    data=ticket_record
                )

                if idx >= total:
                    break

                # 2. Wait 3 seconds for backend registration
                time.sleep(3)

                # 3. Check active session
                session = checkout_client.checkParkingSession()
                seconds_remaining = session.get("seconds_left", duration * 60)
                expire_dt = session.get("expire_dt")

                sleep_duration = max(0.0, seconds_remaining + 3.0)
                self.seconds_remaining = sleep_duration
                self.status = "WAITING_NEXT_TICKET"

                if expire_dt:
                    self.next_ticket_at = expire_dt.isoformat()

                self._emit_log(
                    f"Waiting {int(sleep_duration // 60)}m {int(sleep_duration % 60)}s before next ticket (expires at {expire_dt}).",
                    level="INFO",
                    data={"secondsRemaining": sleep_duration, "nextTicketAt": self.next_ticket_at}
                )

                # 4. Wait in 1-second ticks for immediate cancellation
                end_time = time.time() + sleep_duration
                while time.time() < end_time:
                    if self._stop_event.is_set():
                        self.status = "STOPPED"
                        self._emit_log("Scheduler cancelled during wait period.", level="WARN")
                        return
                    self.seconds_remaining = max(0.0, end_time - time.time())
                    time.sleep(1.0)

            self.status = "COMPLETED"
            self.seconds_remaining = 0.0
            self.next_ticket_at = None
            self._emit_log("All scheduled tickets purchased successfully!", level="SUCCESS")

        except Exception as e:
            self.status = "ERROR"
            self.last_error = str(e)
            self._emit_log(f"Scheduler error: {e}", level="ERROR", data={"error": str(e)})
