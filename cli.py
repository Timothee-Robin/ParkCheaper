import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def ensure_stdio():
    """Ensure sys.stdout, sys.stderr, and sys.stdin are valid stream objects."""
    log_file = None
    appdata = os.getenv("APPDATA")
    if appdata:
        try:
            log_dir = Path(appdata) / "ParkCheaper"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = open(log_dir / "app.log", "a", encoding="utf-8", buffering=1, errors="replace")
        except Exception:
            log_file = None

    fallback_out = log_file if log_file is not None else open(os.devnull, "w", encoding="utf-8")

    if sys.stdout is None:
        sys.stdout = fallback_out
    elif not hasattr(sys.stdout, "isatty"):
        setattr(sys.stdout, "isatty", lambda: False)

    if sys.stderr is None:
        sys.stderr = fallback_out
    elif not hasattr(sys.stderr, "isatty"):
        setattr(sys.stderr, "isatty", lambda: False)

    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r", encoding="utf-8")


ensure_stdio()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from internal.models.account import Account
from internal.client.client import Client
from internal.site.paybyphone.auth import AuthServices
from internal.site.paybyphone.parkingZone import ParkingZone
from internal.site.paybyphone.parkingOptimizer import ParkingOptimizer
from internal.site.paybyphone.checkout import CheckoutClient


def load_credentials():
    candidates = [
        Path.cwd() / ".env",
        Path(sys.executable).parent / ".env",
    ]
    appdata = os.getenv("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "ParkCheaper" / ".env")
        candidates.append(Path(appdata) / "PaybyPhoneBuyer" / ".env")
    candidates.append(Path.home() / ".paybyphone" / ".env")

    for p in candidates:
        if p.is_file():
            load_dotenv(p)
            return


def get_authenticated_client() -> Client:
    load_credentials()
    phone = os.getenv("phone")
    pswd = os.getenv("pswd")
    if not phone or not pswd:
        print("[!] Error: 'phone' or 'pswd' not found in environment, .env file, or AppData.", file=sys.stderr)
        print("[*] Tip: You can create a .env file or configure credentials via the web UI at http://localhost:8000", file=sys.stderr)
        sys.exit(1)

    account = Account(phone, pswd)
    client = Client()
    client.setAccount(account)

    auth = AuthServices(client)
    try:
        auth.login()
        auth.checkAccountdetails()
        auth.checkVehicles()
        auth.checkPayement()
    except Exception as e:
        print(f"[!] PayByPhone authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    return client


def cmd_status(args):
    client = get_authenticated_client()
    print("=" * 60)
    print(" PAYBYPHONE ACCOUNT STATUS")
    print("=" * 60)
    print(f" Member ID     : {client.account.memberId}")
    print(f" Phone         : +{client.account.phone}")
    
    vehicles = client.account.vehiclesList or []
    print(f"\n Registered Vehicles ({len(vehicles)}):")
    for v in vehicles:
        active_mark = " (SELECTED)" if args.plate and v.licensePlate.upper() == args.plate.upper() else ""
        print(f"   • {v.licensePlate} ({v.type}) [ID: {v.vehicleId}]{active_mark}")

    cards = client.account.cardsList or []
    print(f"\n Payment Cards ({len(cards)}):")
    for c in cards:
        print(f"   • {c.maskedCardNumber} ({c.cardType}) [ID: {c.paymentAccountId}]")

    # Check active session
    zone = args.zone or "94802"
    pz = ParkingZone(client, zone, licensePlate=args.plate)
    cc = CheckoutClient(client, [15], pz, licensePlate=args.plate)
    print(f"\n Active Session (Zone {zone} | Plate: {cc.licensePlate}):")
    try:
        session = cc.checkParkingSession()
        expire_dt = session["expire_dt"].strftime("%Y-%m-%d %H:%M:%S UTC")
        mins = int(session["seconds_left"] // 60)
        secs = int(session["seconds_left"] % 60)
        print(f"   [ACTIVE] Expires at {expire_dt} ({mins}m {secs}s remaining)")
    except ValueError:
        print("   [NONE] No active parking session for this vehicle.")
    except Exception as e:
        print(f"   [ERROR] Could not check session: {e}")

    print("=" * 60)


def cmd_optimize(args):
    client = get_authenticated_client()
    pz = ParkingZone(client, args.zone, licensePlate=args.plate)
    optimizer = ParkingOptimizer(step_minutes=15, parkingZone=pz, allow_free_quota_once=not args.no_promo)
    
    print(f"[*] Analyzing tariffs for zone {args.zone} (Plate: {pz.licensePlate})...")
    optimizer.fetch_tariffs()

    result = optimizer.optimize(
        start_time=args.start,
        end_time=args.end,
        duration_minutes=args.duration
    )

    single_ticket = result.get("single_ticket_cost", result.get("without_promo", {}).get("total_cost", result.get("total_cost", 0.0)))
    optimized = result.get("total_cost", 0.0)
    savings = max(0.0, round(single_ticket - optimized, 2))
    percent = round((savings / single_ticket * 100), 1) if single_ticket > 0 else 0.0

    tickets = result.get("tickets", [])
    covered = result.get("covered_minutes", 0)

    is_free = result.get("is_free") or (optimized == 0.0 and single_ticket == 0.0)
    has_promo = result.get("has_promo", "without_promo" in result)

    print("\n" + "=" * 60)
    print(f" OPTIMIZED PARKING PLAN (Zone {args.zone} | Plate: {pz.licensePlate})")
    print("=" * 60)
    print(f" Covered Duration   : {covered // 60}h {covered % 60}m ({covered} minutes)")
    if is_free:
        print(f" Single Ticket Cost : €0.00 (Gratuit)")
        print(f" Optimized Cost     : €0.00 (Gratuit)")
        print(f" Status             : GRATUIT (Dimanche / Jour férié ou Hors heures payantes)")
    else:
        print(f" Single Ticket Cost : €{single_ticket:.2f}")
        print(f" Optimized Cost     : €{optimized:.2f}")
        print(f" Savings vs Single  : -€{savings:.2f} (-{percent}%)")
    print("-" * 60)
    print(f" {'#':<3} | {'DURATION':<10} | {'TYPE':<25}")
    print("-" * 60)
    
    for idx, d in enumerate(tickets, 1):
        if is_free:
            ticket_type = "Gratuit (Free Parking)"
        elif idx == 1 and has_promo:
            ticket_type = "Municipal Free Quota"
        else:
            ticket_type = "Optimized Paid Ticket"
        print(f" {idx:<3} | {d:>4} min    | {ticket_type}")

    print("=" * 60)
    tickets_str = ",".join(str(d) for d in tickets)
    plate_arg = f" --plate {pz.licensePlate}" if pz.licensePlate else ""
    print(f"\nTo execute this automated schedule:\n  python cli.py schedule --zone {args.zone}{plate_arg} --tickets {tickets_str}\n")


def cmd_buy(args):
    client = get_authenticated_client()
    pz = ParkingZone(client, args.zone, licensePlate=args.plate)
    cc = CheckoutClient(client, [args.duration], pz, licensePlate=args.plate)
    
    print(f"[*] Purchasing single ticket of {args.duration} min in zone {args.zone}...")
    print(f"    Vehicle : {cc.licensePlate} | Card : {cc.payment.maskedCardNumber}")
    
    try:
        res = cc.checkoutTicket(args.duration)
        print(f"[+] Success! 3DS Status: {res.get('status')} | Job ID: {res.get('jobId')}")
    except Exception as e:
        print(f"[!] Checkout error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_schedule(args):
    client = get_authenticated_client()
    pz = ParkingZone(client, args.zone, licensePlate=args.plate)
    tickets = [int(t.strip()) for t in args.tickets.split(",") if t.strip()]
    if not tickets:
        print("[!] No ticket durations specified.", file=sys.stderr)
        sys.exit(1)

    cc = CheckoutClient(client, tickets, pz, licensePlate=args.plate)
    total = len(tickets)

    print("=" * 60)
    print(f" STARTING SEQUENTIAL SCHEDULER ({total} TICKETS)")
    print("=" * 60)
    print(f" Zone      : {args.zone}")
    print(f" Vehicle   : {cc.licensePlate}")
    print(f" Card      : {cc.payment.maskedCardNumber}")
    print(f" Sequence  : {tickets} minutes")
    print(" Press Ctrl+C at any time to safely stop.")
    print("-" * 60)

    try:
        for idx, duration in enumerate(tickets, 1):
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Purchasing ticket {idx}/{total} : {duration} min...")
            res = cc.checkoutTicket(duration)
            print(f"[OK] Purchase confirmed (3DS Status: {res.get('status')}).")

            if idx >= total:
                break

            time.sleep(3)
            session = cc.checkParkingSession()
            seconds_left = max(0.0, session.get("seconds_left", duration * 60) + 3.0)
            expire_dt = session.get("expire_dt").strftime("%H:%M:%S UTC") if session.get("expire_dt") else "unknown"

            print(f"[*] Ticket active until {expire_dt}. Waiting {int(seconds_left // 60)}m {int(seconds_left % 60)}s...")

            end_time = time.time() + seconds_left
            while time.time() < end_time:
                remaining = max(0, int(end_time - time.time()))
                print(f"\r    Next ticket in: {remaining // 60:02d}:{remaining % 60:02d} ", end="", flush=True)
                time.sleep(1)
            print()

        print("\n" + "=" * 60)
        print(" [+] ALL TICKETS PURCHASED SUCCESSFULLY")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n[!] Manual interruption received (Ctrl+C). Scheduler stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error during scheduling: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_serve(args):
    import uvicorn
    import webbrowser
    import threading
    from server.app import app
    from server.tray import SystemTrayApp

    host = getattr(args, "host", None) or "127.0.0.1"
    port = getattr(args, "port", None) or 8000
    no_browser = getattr(args, "no_browser", False)
    no_tray = getattr(args, "no_tray", False)
    hide_console = getattr(args, "hide_console", False)

    if hide_console and sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    url = f"http://{host}:{port}"
    print("=" * 60)
    print(" PARKCHEAPER DESK")
    print("=" * 60)
    print(f" Local Web UI   : {url}")
    print(f" REST & WS API  : {url}/api/...")
    if not no_tray:
        print(" System Tray    : Active (check Windows hide bar / taskbar tray)")
    if not no_browser:
        print(" Launching default web browser...")
    print(" Press Ctrl+C at any time to safely terminate the server.")
    print("=" * 60)

    ensure_stdio()
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config=config)

    tray_app = None
    if not no_tray:
        def on_tray_quit():
            server.should_exit = True
        tray_app = SystemTrayApp(host=host, port=port, on_quit=on_tray_quit)
        tray_app.start()

    if not no_browser:
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.run()
    finally:
        if tray_app:
            tray_app.stop()


def main(args_list=None):
    parser = argparse.ArgumentParser(
        description="PayByPhone Smart Buyer - CLI tool & local web server for automated parking optimization"
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch local web server and open UI in browser")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    p_serve.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    p_serve.add_argument("--no-tray", action="store_true", help="Disable system tray icon")
    p_serve.add_argument("--hide-console", action="store_true", help="Hide console window on startup")
    p_serve.set_defaults(func=cmd_serve)

    # status
    p_status = subparsers.add_parser("status", help="Display account status, registered vehicles, and active session")
    p_status.add_argument("--zone", default="94802", help="PayByPhone zone code (default: 94802)")
    p_status.add_argument("-p", "--plate", help="Filter or specify vehicle license plate")
    p_status.set_defaults(func=cmd_status)

    # optimize
    p_opt = subparsers.add_parser("optimize", help="Calculate optimal ticket combination for given duration")
    p_opt.add_argument("--zone", default="94802", help="Zone code (default: 94802)")
    p_opt.add_argument("-p", "--plate", help="License plate (default: primary vehicle)")
    p_opt.add_argument("--start", help="Start time in HH:MM (e.g. 14:00)")
    p_opt.add_argument("--end", help="End time in HH:MM (e.g. 17:30)")
    p_opt.add_argument("--duration", type=int, help="Total duration in minutes (e.g. 210)")
    p_opt.add_argument("--no-promo", action="store_true", help="Ignore free municipal quota")
    p_opt.set_defaults(func=cmd_optimize)

    # buy
    p_buy = subparsers.add_parser("buy", help="Purchase a single ticket immediately")
    p_buy.add_argument("--zone", default="94802", required=True, help="Zone code")
    p_buy.add_argument("-p", "--plate", help="License plate to use (default: primary vehicle)")
    p_buy.add_argument("--duration", type=int, required=True, help="Duration in minutes")
    p_buy.set_defaults(func=cmd_buy)

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Run sequential automated ticket scheduler")
    p_sched.add_argument("--zone", default="94802", required=True, help="Zone code")
    p_sched.add_argument("-p", "--plate", help="License plate to use (default: primary vehicle)")
    p_sched.add_argument("--tickets", required=True, help="Comma-separated ticket durations in minutes (e.g. 30,90,90)")
    p_sched.set_defaults(func=cmd_schedule)

    raw_args = args_list if args_list is not None else sys.argv[1:]
    if not raw_args:
        raw_args = ["serve"]

    parsed = parser.parse_args(raw_args)
    if hasattr(parsed, "func"):
        parsed.func(parsed)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

