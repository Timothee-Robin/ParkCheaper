import sys
import os
import time
import webbrowser
from pathlib import Path
from PIL import Image, ImageDraw
import pystray


def get_tray_image() -> Image.Image:
    """Load the high-res app icon or generate a fallback icon dynamically."""
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "installer" / "app_icon.png")
    candidates.append(Path(__file__).resolve().parents[1] / "installer" / "app_icon.png")
    candidates.append(Path.cwd() / "installer" / "app_icon.png")

    for p in candidates:
        if p.is_file():
            try:
                return Image.open(p)
            except Exception:
                pass

    # Fallback: clean 64x64 dark zinc & emerald badge
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, 62, 62], radius=14, fill=(18, 18, 24), outline=(52, 211, 153), width=3)
    draw.rectangle([20, 16, 26, 48], fill=(255, 255, 255))
    draw.rounded_rectangle([20, 16, 44, 34], radius=6, outline=(255, 255, 255), width=6)
    return img


class SystemTrayApp:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000, on_quit=None):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.on_quit_callback = on_quit
        self.icon: pystray.Icon | None = None

    def open_dashboard(self, icon=None, item=None):
        webbrowser.open(self.url)

    def quit_app(self, icon=None, item=None):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        if self.on_quit_callback:
            try:
                self.on_quit_callback()
            except Exception:
                pass

    def start(self):
        image = get_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Open Web Dashboard", self.open_dashboard, default=True),
            pystray.MenuItem(f"Dashboard URL: {self.url}", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit PayByPhone Buyer", self.quit_app)
        )
        self.icon = pystray.Icon(
            name="PaybyPhoneBuyer",
            icon=image,
            title=f"PayByPhone Buyer ({self.url})",
            menu=menu
        )
        self.icon.run_detached()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
