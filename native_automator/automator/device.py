"""
native_automator — native Android UI automation via MacroDroid + AutoInput.
=======================================================================

Usage:
    from automator import Device, By

    d = Device()
    d.open_app("com.whatsapp")
    d.find(By.TEXT, "Search").click()
    d.type_text("Hello")
    d.swipe(300, 900, 300, 300)
    d.back()
"""

import urllib.request, urllib.parse, json, time
from .exceptions import DeviceError, ConnectionError, ElementNotFound, ActionFailed
from .elements import By
from .gestures import Gestures


class Element:
    """Represents a UI element. Created by Device.find()."""

    def __init__(self, device, by, value):
        self._device = device
        self._by = by
        self._value = value

    def click(self):
        return self._device._click(self._by, self._value)

    def text(self):
        return self._device._get_element_text(self._by, self._value)

    def exists(self):
        return self._device._element_exists(self._by, self._value)

    def wait_until_gone(self, timeout=10):
        for _ in range(timeout):
            if not self.exists():
                return True
            time.sleep(1)
        return False

    def __repr__(self):
        return f"<Element by={self._by} value='{self._value}'>"


class Device:
    """Main interface to the Android device via MacroDroid HTTP server."""

    def __init__(self, host="127.0.0.1", port=8580, timeout=10):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._base = f"http://{host}:{port}"
        self.gestures = Gestures()

    def _get(self, endpoint, params=None):
        url = self._base + endpoint
        if params:
            qs = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url += "?" + qs
        try:
            r = urllib.request.urlopen(url, timeout=self._timeout)
            body = r.read().decode()
            if body.strip():
                return json.loads(body)
            return {"status": "ok"}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code == 404:
                raise ActionFailed(f"Macro not found at {endpoint} — create it in MacroDroid")
            raise ActionFailed(f"HTTP {e.code}: {msg}")
        except urllib.error.URLError:
            raise ConnectionError(
                f"Cannot reach MacroDroid at {self._base}. "
                "Is the HTTP server enabled? (Settings → HTTP Server)"
            )
        except Exception as e:
            raise DeviceError(str(e))

    def _click(self, by, value):
        endpoints = {
            By.TEXT: ("/click/text", {"q": value}),
            By.ID: ("/click/id", {"id": value}),
            By.XPATH: ("/click/xpath", {"xpath": value}),
            By.COORD: ("/click/coord", {"x": value[0], "y": value[1]}),
        }
        ep, params = endpoints.get(by)
        if not ep:
            raise DeviceError(f"Unknown selector: {by}")
        return self._get(ep, params)

    def _element_exists(self, by, value):
        if by == By.TEXT:
            try:
                self._get("/text/exists", {"q": value})
                return True
            except (ActionFailed, ElementNotFound):
                return False
        return False  # only TEXT supported for existence check

    def _get_element_text(self, by, value):
        if by == By.TEXT:
            return value  # elements found by text already have the text
        return ""

    # ── Main API ──────────────────────────────────────────

    def find(self, by, value):
        """Find a UI element. Returns an Element (lazy — no round-trip until .click())."""
        return Element(self, by, value)

    def click_text(self, text, exact=False):
        """Find and click text."""
        params = {"q": text}
        if exact:
            params["exact"] = "1"
        return self._get("/click/text", params)

    def click_id(self, resource_id):
        """Click by Android resource ID."""
        return self._get("/click/id", {"id": resource_id})

    def click_xpath(self, xpath):
        """Click by XPath."""
        return self._get("/click/xpath", {"xpath": xpath})

    def click_coord(self, x, y):
        """Tap at coordinates."""
        return self._get("/click/coord", {"x": x, "y": y})

    def type_text(self, text, clear_first=False):
        """Type text into the focused element."""
        params = {"text": text}
        if clear_first:
            params["clear"] = "1"
        return self._get("/input/text", params)

    def type_text_slow(self, text, delay_ms=80):
        """Type text with per-character delay (looks human)."""
        for ch in text:
            self._get("/input/text", {"text": ch})
            time.sleep(delay_ms / 1000)
        return {"status": "ok"}

    def swipe(self, x1, y1, x2, y2, duration=300):
        """Swipe gesture."""
        return self._get("/swipe", {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration
        })

    def scroll_down(self):
        """Scroll down one screen."""
        s = Gestures.swipe_up()
        return self.swipe(**s)

    def scroll_up(self):
        """Scroll up one screen."""
        s = Gestures.swipe_down()
        return self.swipe(**s)

    def back(self):
        """System back button."""
        return self._get("/back")

    def home(self):
        """Go to home screen."""
        return self._get("/home")

    def recent_apps(self):
        """Show recent apps (Overview)."""
        return self._get("/recent")

    def open_app(self, package, activity=None):
        """Launch an app by package name."""
        params = {"package": package}
        if activity:
            params["activity"] = activity
        return self._get("/app/open", params)

    def wait(self, seconds):
        """Sleep."""
        time.sleep(seconds)
        return {"status": "ok"}

    def text_exists(self, text, timeout=1):
        """Check if text is visible on screen."""
        try:
            r = self._get("/text/exists", {"q": text, "timeout": timeout})
            return r.get("found", False)
        except (ActionFailed, ConnectionError):
            return False

    def wait_for_text(self, text, timeout=15):
        """Wait up to <timeout> seconds for <text> to appear. Returns True if found."""
        for _ in range(timeout):
            if self.text_exists(text):
                return True
            time.sleep(1)
        return False

    def kill_app(self, package):
        """Force-stop an app."""
        return self._get("/app/kill", {"package": package})

    def notification(self, title, text):
        """Send a notification to the status bar."""
        return self._get("/notification", {"title": title, "text": text})

    def screenshot(self, path="/sdcard/automator_screen.png"):
        """Capture screen."""
        return self._get("/screenshot", {"path": path})

    def get_clipboard(self):
        """Read clipboard text."""
        r = self._get("/clipboard/get")
        return r.get("text", "")

    def set_clipboard(self, text):
        """Write text to clipboard."""
        return self._get("/clipboard/set", {"text": text})

    # ── Power / system ────────────────────────────────────

    def screen_on(self):
        """Turn screen on."""
        return self._get("/screen/on")

    def screen_off(self):
        """Turn screen off."""
        return self._get("/screen/off")

    def volume_up(self):
        """Raise volume."""
        return self._get("/volume/up")

    def volume_down(self):
        """Lower volume."""
        return self._get("/volume/down")

    def is_locked(self):
        """Check if device is locked."""
        try:
            r = self._get("/screen/locked")
            return r.get("locked", True)
        except (ActionFailed, ConnectionError):
            return True

    # ── Context manager ───────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __repr__(self):
        return f"<Device {self._host}:{self._port}>"
