import os
import sys
import multiprocessing
from pathlib import Path

def ensure_stdio():
    """Ensure sys.stdout, sys.stderr, and sys.stdin are valid stream objects.

    When running as a GUI application on Windows (e.g. PyInstaller console=False
    or pythonw), sys.stdout, sys.stderr, and sys.stdin are None.
    Libraries like Uvicorn check `sys.stdout.isatty()` during logging configuration,
    which raises `AttributeError: 'NoneType' object has no attribute 'isatty'`.
    Redirecting them to a persistent log file in AppData resolves this and enables
    background logging.
    """
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

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()

    raw_args = sys.argv[1:]
    is_cli = bool(raw_args and raw_args[0] in ("status", "optimize", "buy", "schedule", "--help", "-h"))

    if is_cli:
        # Attach to the caller's console if running as a windowed application
        if sys.platform == "win32":
            try:
                import ctypes
                if ctypes.windll.kernel32.AttachConsole(-1):
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            except Exception:
                pass
    else:
        # Running in web / tray mode: hide any visible console window immediately
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 0) # SW_HIDE
            except Exception:
                pass

    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
