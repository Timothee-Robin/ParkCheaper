import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from starlette.requests import HTTPConnection
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.models.account import Account
from internal.client.client import Client
from internal.site.paybyphone.auth import AuthServices
from internal.site.paybyphone.parkingZone import ParkingZone
from internal.site.paybyphone.parkingOptimizer import ParkingOptimizer
from internal.site.paybyphone.checkout import CheckoutClient
from server.scheduler import ParkingScheduler


# --- Credentials Management ---

def get_env_paths() -> list[Path]:
    paths = [
        Path.cwd() / ".env",
        Path(sys.executable).parent / ".env",
    ]
    appdata = os.getenv("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "PaybyPhoneBuyer" / ".env")
    paths.append(Path.home() / ".paybyphone" / ".env")
    return paths

def load_credentials():
    for p in get_env_paths():
        if p.is_file():
            load_dotenv(p)
            return

def save_credentials(phone: str, pswd: str):
    appdata = os.getenv("APPDATA")
    if appdata:
        target_dir = Path(appdata) / "PaybyPhoneBuyer"
    else:
        target_dir = Path.cwd()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        env_file = target_dir / ".env"
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"phone={phone}\npswd={pswd}\n")
    except Exception as e:
        print(f"[!] Warning: Could not persist credentials to {target_dir}: {e}")
    os.environ["phone"] = phone
    os.environ["pswd"] = pswd


# --- Lifespan Management ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_credentials()
    phone = os.getenv("phone")
    pswd = os.getenv("pswd")
    
    client = None
    if phone and pswd:
        try:
            print("[*] Initial PayByPhone connection...")
            account = Account(phone, pswd)
            client = Client()
            client.setAccount(account)
            
            auth = AuthServices(client)
            auth.login()
            auth.checkAccountdetails()
            auth.checkVehicles()
            auth.checkPayement()
            print(f"[+] Client connected successfully (+{phone})!")
        except Exception as e:
            print(f"[!] Automatic PayByPhone login failed: {e}")
            client = None
    else:
        print("[!] No 'phone' or 'pswd' credentials found in environment or AppData.")

    app.state.client = client
    app.state.scheduler = ParkingScheduler()
    
    yield
    
    # Cleanup
    if app.state.client and hasattr(app.state.client, "session"):
        print("[-] Closing PayByPhone HTTP session...")
        app.state.client.session.close()


# --- Application Setup ---

app = FastAPI(
    title="PayByPhone Buyer API",
    description="REST & WebSocket API for PayByPhone parking optimization and automation",
    version="1.0.0",
    lifespan=lifespan
)

app.state.client = None
app.state.scheduler = ParkingScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client(conn: HTTPConnection) -> Client:
    client = getattr(conn.app.state, "client", None)
    if not client:
        raise HTTPException(
            status_code=503,
            detail="PayByPhone client not connected. Check your credentials or call /api/auth/login."
        )
    return client

def get_scheduler(conn: HTTPConnection) -> ParkingScheduler:
    scheduler = getattr(conn.app.state, "scheduler", None)
    if scheduler is None:
        scheduler = ParkingScheduler()
        conn.app.state.scheduler = scheduler
    return scheduler


# --- Pydantic Schemas ---

class LoginRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format (e.g. 33612345678)")
    pswd: str = Field(..., description="PayByPhone account password")

class OptimizeRequest(BaseModel):
    zone: str = Field(..., description="Parking zone code (e.g. 94802)")
    startTime: str | None = Field(None, description="Start time in HH:MM format (e.g. 14:00)")
    endTime: str | None = Field(None, description="End time in HH:MM format (e.g. 17:30)")
    durationMinutes: int | None = Field(None, description="Total duration in minutes (alternative to start/end times)")
    allowFreeQuota: bool = Field(True, description="Allow using the free quota")
    licensePlate: str | None = Field(None, description="License plate to use (defaults to primary vehicle)")

class BuyTicketRequest(BaseModel):
    zone: str = Field(..., description="Parking zone code")
    durationMinutes: int = Field(..., ge=1, description="Ticket duration in minutes to buy")
    licensePlate: str | None = Field(None, description="License plate to use (defaults to primary vehicle)")

class StartSchedulerRequest(BaseModel):
    zone: str = Field(..., description="Parking zone code")
    ticketList: list[int] = Field(..., min_length=1, description="List of ticket durations in minutes to buy sequentially")
    licensePlate: str | None = Field(None, description="License plate to use (defaults to primary vehicle)")


# --- Routes: Authentication & Profile ---

@app.get("/api/auth/profile", summary="Get profile and account details")
def get_profile(client: Client = Depends(get_client)):
    vehicles = [
        {"type": v.type, "licensePlate": v.licensePlate, "vehicleId": v.vehicleId}
        for v in (client.account.vehiclesList or [])
    ]
    cards = [
        {"maskedCardNumber": c.maskedCardNumber, "cardType": c.cardType, "paymentAccountId": c.paymentAccountId}
        for c in (client.account.cardsList or [])
    ]
    
    return {
        "connected": True,
        "phone": client.account.phone,
        "memberId": client.account.memberId,
        "vehicles": vehicles,
        "cards": cards,
        "activeVehicle": vehicles[0]["licensePlate"] if vehicles else None,
        "activeCard": cards[0]["maskedCardNumber"] if cards else None
    }

@app.post("/api/auth/login", summary="Login or change credentials")
def login(req: LoginRequest, request: Request):
    try:
        account = Account(req.phone, req.pswd)
        client = Client()
        client.setAccount(account)
        
        auth = AuthServices(client)
        auth.login()
        auth.checkAccountdetails()
        auth.checkVehicles()
        auth.checkPayement()
        
        request.app.state.client = client
        save_credentials(req.phone, req.pswd)
        return {"status": "SUCCESS", "message": "Login successful and credentials saved."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login error: {e}")


# --- Routes: Zone & Optimizer ---

@app.get("/api/zones/{zone_id}/info", summary="Zone information and restrictions")
def get_zone_info(zone_id: str, licensePlate: str | None = None, client: Client = Depends(get_client)):
    try:
        pz = ParkingZone(client, zone_id, licensePlate=licensePlate)
        pz.getRestrictionOnZone()
        return {
            "zone": pz.zone,
            "ratePolicyId": pz.ratePolicyId,
            "maxStayMinutes": pz.maxStay,
            "licensePlate": pz.licensePlate
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving zone info: {e}")

@app.post("/api/optimizer/calculate", summary="Calculate pricing optimization")
def calculate_optimization(req: OptimizeRequest, client: Client = Depends(get_client)):
    try:
        pz = ParkingZone(client, req.zone, licensePlate=req.licensePlate)
        optimizer = ParkingOptimizer(
            step_minutes=15,
            parkingZone=pz,
            allow_free_quota_once=req.allowFreeQuota
        )
        optimizer.fetch_tariffs()
        
        result = optimizer.optimize(
            start_time=req.startTime,
            end_time=req.endTime,
            duration_minutes=req.durationMinutes
        )
        
        # Formatted cleanly for React UI & CLI (comparison against a single ticket)
        single_ticket_cost = result.get("single_ticket_cost", result.get("without_promo", {}).get("total_cost", result.get("total_cost", 0.0)))
        optimized_cost = result.get("total_cost", 0.0)
        savings_amount = max(0.0, round(single_ticket_cost - optimized_cost, 2))
        savings_percent = round((savings_amount / single_ticket_cost * 100), 1) if single_ticket_cost > 0 else 0.0
        
        return {
            "zone": req.zone,
            "licensePlate": pz.licensePlate,
            "tickets": result.get("tickets", []),
            "coveredMinutes": result.get("covered_minutes", 0),
            "totalCost": optimized_cost,
            "standardCost": single_ticket_cost,
            "singleTicketCost": single_ticket_cost,
            "savingsAmount": savings_amount,
            "savingsPercent": savings_percent,
            "hasPromo": result.get("has_promo", "without_promo" in result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Optimization error: {e}")


# --- Routes: Active Session ---

@app.get("/api/session/active", summary="Active parking session status")
def get_active_session(zone: str | None = None, licensePlate: str | None = None, client: Client = Depends(get_client)):
    try:
        target_zone = zone or "94802"
        pz = ParkingZone(client, target_zone, licensePlate=licensePlate)
        cc = CheckoutClient(client=client, ticketList=[15], parkingZone=pz, licensePlate=licensePlate)
        session_info = cc.checkParkingSession()
        
        return {
            "hasActiveSession": True,
            "sessionId": session_info.get("session_id"),
            "licensePlate": cc.licensePlate,
            "expireDtUtc": session_info.get("expire_dt").isoformat() if session_info.get("expire_dt") else None,
            "secondsRemaining": max(0.0, round(session_info.get("seconds_left", 0.0), 1))
        }
    except ValueError:
        return {"hasActiveSession": False, "licensePlate": licensePlate, "secondsRemaining": 0.0}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error checking session: {e}")


# --- Routes: Checkout & Scheduler ---

@app.post("/api/checkout/ticket", summary="Purchase a single ticket immediately")
def buy_ticket(req: BuyTicketRequest, client: Client = Depends(get_client)):
    try:
        pz = ParkingZone(client, req.zone, licensePlate=req.licensePlate)
        cc = CheckoutClient(client=client, ticketList=[req.durationMinutes], parkingZone=pz, licensePlate=req.licensePlate)
        result = cc.checkoutTicket(req.durationMinutes)
        return {
            "status": "SUCCESS",
            "licensePlate": cc.licensePlate,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Checkout error: {e}")

@app.post("/api/session/start", summary="Start automated background scheduler")
def start_scheduler(
    req: StartSchedulerRequest,
    client: Client = Depends(get_client),
    scheduler: ParkingScheduler = Depends(get_scheduler)
):
    try:
        pz = ParkingZone(client, req.zone, licensePlate=req.licensePlate)
        cc = CheckoutClient(client=client, ticketList=req.ticketList, parkingZone=pz, licensePlate=req.licensePlate)
        scheduler.start(cc)
        return {
            "status": "STARTED",
            "zone": req.zone,
            "licensePlate": cc.licensePlate,
            "ticketList": req.ticketList,
            "message": f"Scheduler successfully started for {len(req.ticketList)} ticket(s)."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not start scheduler: {e}")

@app.get("/api/session/status", summary="Scheduler status and progress")
def get_scheduler_status(scheduler: ParkingScheduler = Depends(get_scheduler)):
    return scheduler.get_state()

@app.post("/api/session/stop", summary="Stop scheduler immediately")
def stop_scheduler(scheduler: ParkingScheduler = Depends(get_scheduler)):
    return scheduler.stop()


# --- WebSocket: Streaming des événements & logs en temps réel ---

@app.websocket("/api/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    scheduler = getattr(websocket.app.state, "scheduler", None)
    if scheduler is None:
        scheduler = ParkingScheduler()
        websocket.app.state.scheduler = scheduler
    queue = asyncio.Queue()

    def listener(event: dict[str, Any]):
        try:
            queue.put_nowait(event)
        except Exception:
            pass

    scheduler.add_log_listener(listener)
    try:
        # Envoi de l'état initial dès la connexion
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "state": scheduler.get_state()
        })

        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        scheduler.remove_log_listener(listener)


# --- Static Frontend Mounting ---

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    STATIC_DIR = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    STATIC_DIR = PROJECT_ROOT / "frontend" / "dist"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)