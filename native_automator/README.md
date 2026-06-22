# native_automator

**native Android UI automation from Termux — no root, no ADB, no laptop.**

Uses MacroDroid HTTP Server + AutoInput plugin to control any app via
AccessibilityService. Your Python scripts call familiar Selenium-like
methods (`click_text`, `click_id`, `swipe`, etc.) via HTTP to localhost.

## Architecture

```
Your Python script  →  HTTP GET  →  MacroDroid HTTP Server (localhost:8580)
                                        │
                                   [trigger fires macro]
                                        │
                                   AutoInput (AccessibilityService)
                                        │
                                   UI action on your app
```

## Quick Start

### 1. Install apps on your phone

| App | Purpose |
|-----|---------|
| [MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) | Automation engine + HTTP server |
| [AutoInput](https://play.google.com/store/apps/details?id=com.joaomgcd.autoinput) | UI interaction plugin |

Enable Accessibility for both:

```
Settings → Accessibility → MacroDroid → ON
Settings → Accessibility → AutoInput → ON
```

### 2. Enable MacroDroid HTTP Server

```
MacroDroid → Settings → HTTP Server → ON (port 8580)
```

### 3. Create the macros

```bash
python3 setup_macros.py
```

Follow the interactive guide — it walks you through creating 22 macros,
one at a time with clear instructions.

### 4. Test the connection

```bash
python3 scripts/test_connection.py
```

### 5. Start automating

```python
from automator import Device

d = Device()
d.open_app("com.whatsapp")
d.click_text("Search")
d.type_text("Hello")
d.click_id("com.whatsapp:id/send")
d.back()
```

## API Reference

### Element Finding

| Method | Example |
|--------|---------|
| `click_text("Login")` | Click first visible element containing text "Login" |
| `click_id("com.app:id/btn")` | Click by Android resource ID |
| `click_xpath("//Button[@text='Go']")` | Click by XPath |
| `click_coord(500, 1000)` | Tap at exact coordinates |

### Input

| Method | Example |
|--------|---------|
| `type_text("hello")` | Type text into focused element |
| `type_text_slow("hello", delay_ms=80)` | Type with per-character delay |

### Navigation

| Method | Example |
|--------|---------|
| `back()` | System back button |
| `home()` | Go to home screen |
| `recent_apps()` | Show recent apps overview |
| `open_app("com.whatsapp")` | Launch an app |
| `kill_app("com.whatsapp")` | Force-stop an app |

### Scrolling & Gestures

| Method | Example |
|--------|---------|
| `scroll_down()` | Swipe up (scroll down one screen) |
| `scroll_up()` | Swipe down (scroll up one screen) |
| `swipe(x1, y1, x2, y2, duration)` | Custom swipe |
| `d.gestures.swipe_left()` | Pre-built swipe left |
| `d.gestures.human_swipe_up()` | Randomized human-like swipe |

### Waiting & Detection

| Method | Example |
|--------|---------|
| `wait_for_text("Loading", timeout=15)` | Wait for text to appear |
| `text_exists("Hello", timeout=2)` | Check if text is visible |
| `wait(3)` | Sleep for N seconds |

### System

| Method | Example |
|--------|---------|
| `screenshot()` | Capture screen |
| `screen_on()` / `screen_off()` | Toggle screen |
| `volume_up()` / `volume_down()` | Adjust volume |
| `notification("Title", "Body")` | Post notification |
| `get_clipboard()` / `set_clipboard("text")` | Read/write clipboard |
| `is_locked()` | Check if device is locked |

## Finding Element Selectors

Use the recorder tool to discover selectors interactively:

```bash
# Opens the app and lets you test click by text, ID, XPath, or coordinates
python3 scripts/record.py com.whatsapp
```

Commands in the recorder:
- `t Login` — test click by text
- `i com.app:id/btn` — test click by ID
- `x //Button[@text='Go']` — test click by XPath
- `c 500 1000` — test click by coordinates
- `s` — take screenshot
- `q` — quit

Alternatively, use **AutoInput UI Query** from inside MacroDroid to see
the current screen's element hierarchy with IDs and text.

## Requirements

- Python 3.8+ (stdlib only — no pip dependencies required)
- MacroDroid (with HTTP Server enabled)
- AutoInput plugin
- Both apps with Accessibility Service enabled

## No root. No ADB. No laptop.

Everything runs on-device in Termux. The screen is NOT captured by the
script — you can use the phone normally while automation runs in the
background via AccessibilityService.
