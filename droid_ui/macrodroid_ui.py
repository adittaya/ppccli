"""
droid_ui — native Android UI automation via MacroDroid + AutoInput
=================================================================
Usage:
    from droid_ui import Device

    d = Device(port=8580)  # MacroDroid HTTP server port
    d.open_app("com.whatsapp")
    d.click_text("Search")
    d.type_text("hello")
    d.click_id("com.whatsapp:id/btn_send")
    d.back()
    d.swipe(300, 900, 300, 300)
    d.wait(3)
"""

import urllib.request, urllib.parse, json, time

class UIError(Exception):
    pass

class Device:
    """Controls the Android device via MacroDroid + AutoInput HTTP triggers."""

    def __init__(self, host="127.0.0.1", port=8580, timeout=10):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        # Each action corresponds to a MacroDroid macro endpoint.
        # User must create these macros manually (see setup_guide.md).
        self._actions = {
            "click_text": "/click/text",
            "click_id": "/click/id",
            "click_xpath": "/click/xpath",
            "click_coord": "/click/coord",
            "type_text": "/input/text",
            "swipe": "/swipe",
            "back": "/back",
            "home": "/home",
            "open_app": "/app/open",
            "scroll_down": "/scroll/down",
            "scroll_up": "/scroll/up",
            "wait": "/wait",
        }

    def _get(self, endpoint, params=None):
        url = self.base + endpoint
        if params:
            qs = urllib.parse.urlencode(params)
            url += "?" + qs
        try:
            r = urllib.request.urlopen(url, timeout=self.timeout)
            body = r.read().decode()
            if body.strip():
                return json.loads(body)
            return {"status": "ok"}
        except urllib.error.HTTPError as e:
            raise UIError(f"HTTP {e.code}: {e.read().decode()[:200]}")
        except urllib.error.URLError as e:
            raise UIError(f"Connection refused — is MacroDroid HTTP server running on {self.base}?")
        except Exception as e:
            raise UIError(str(e))

    # ── High-level API ──────────────────────────────────────

    def click_text(self, text, exact=False):
        """Click the first visible element containing <text>."""
        p = {"q": text}
        if exact:
            p["exact"] = "1"
        return self._get("/click/text", p)

    def click_id(self, resource_id):
        """Click element by Android resource ID (e.g. 'com.app:id/btn')."""
        return self._get("/click/id", {"id": resource_id})

    def click_xpath(self, xpath):
        """Click element by XPath (e.g. '//android.widget.Button[@text=\"Login\"]')."""
        return self._get("/click/xpath", {"xpath": xpath})

    def click_coord(self, x, y):
        """Tap at exact screen coordinates."""
        return self._get("/click/coord", {"x": x, "y": y})

    def type_text(self, text):
        """Type text into the currently focused element."""
        return self._get("/input/text", {"text": text})

    def swipe(self, x1, y1, x2, y2, duration=300):
        """Swipe from (x1,y1) to (x2,y2) over <duration> ms."""
        return self._get("/swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration})

    def scroll_down(self, steps=1):
        """Scroll the page down <steps> times."""
        return self._get("/scroll/down", {"steps": steps})

    def scroll_up(self, steps=1):
        """Scroll the page up <steps> times."""
        return self._get("/scroll/up", {"steps": steps})

    def back(self):
        """Press the system back button."""
        return self._get("/back")

    def home(self):
        """Go to the home screen."""
        return self._get("/home")

    def open_app(self, package, activity=None):
        """Launch an app by package name.
        
        Optionally specify activity: e.g. '.MainActivity'
        """
        p = {"package": package}
        if activity:
            p["activity"] = activity
        return self._get("/app/open", p)

    def wait(self, seconds):
        """Do nothing for <seconds> (useful for page loads)."""
        time.sleep(seconds)
        return {"status": "ok"}

    def text_exists(self, text):
        """Check if <text> appears anywhere on screen.
        
        Returns True/False. Requires a 'text_exists' macro.
        """
        try:
            r = self._get("/text/exists", {"q": text})
            return r.get("found", False)
        except UIError:
            return False

    def get_text(self):
        """Get all visible text on screen.
        
        Returns a string. Requires a 'get_text' macro.
        """
        r = self._get("/get/text")
        return r.get("text", "")

    def screenshot(self, path="/sdcard/screen.png"):
        """Capture the screen and save to <path>.
        
        Requires: cmd uiautomator (if available) or Screenshot action.
        """
        return self._get("/screenshot", {"path": path})
