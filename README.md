<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

# ppccli — PPC Page Flow Navigator

Automated PPC page navigation tool. Navigates through PPC networks (VPLINK, AroLinks, LinkPays) automatically — from the initial hittracks link to the final destination URL.

## Quick Start

**One command — install everything:**

```bash
git clone https://github.com/adittaya/ppccli.git
cd ppccli
bash setup.sh
```

This installs Chromium, chromedriver, Xvfb, x11vnc, Python packages, and creates the `ppccli` command. Then you can run:

```bash
# Interactive mode (recommended for first use)
ppccli -i

# Or pass a URL directly
ppccli "https://arolinks.com/zREqi"
```

## Usage

### Basic

```bash
# Single URL, one view
ppccli "https://arolinks.com/zREqi"

# With VNC disabled (headless — saves RAM)
ppccli --no-vnc "https://arolinks.com/zREqi"

# Multiple views
ppccli -n 5 "https://arolinks.com/zREqi"

# With YouTube referrer
ppccli -r "https://youtu.be/8A2LHzyevJA" "https://vplink.in/MGIt8"
```

### Parallel (multiple URLs at once)

```bash
# Two workers, one session, headless
ppccli -p --all-parallel --no-vnc \
  -n 100 -w 1 \
  -r "https://youtu.be/8A2LHzyevJA" \
  "https://arolinks.com/zREqi" \
  "https://vplink.in/MGIt8"
```

Flags:
| Flag | Purpose |
|------|---------|
| `-p` | Parallel mode |
| `--all-parallel` | All workers in one session (same IP) |
| `--no-vnc` | Skip VNC (headless Chromium) |
| `-n N` | Number of sessions |
| `-w N` | Windows per URL |
| `-r URL` | YouTube referrer |
| `--no-rotate` | Skip IP rotation |
| `-i` | Interactive mode |

### Interactive mode

```
ppccli -i

  ╔══════════════════════════════════════╗
  ║           ppccli — Interactive       ║
  ╚══════════════════════════════════════╝

  Mode: (s)ingle or (p)arallel? [s]: p
  Enter URLs for each network (blank to skip)...
```

## IP Rotation

ppccli toggles airplane mode on an Android device via MacroDroid to rotate IPs between sessions.

**One-time setup:**

1. Install [MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) + [AutoInput](https://play.google.com/store/apps/details?id=com.joaomgcd.autoinput) on Android
2. Enable Accessibility Service for both apps
3. Enable MacroDroid HTTP Server (Settings → HTTP Server, port `8080`)
4. Create a macro: HTTP trigger `/rotate_ip` → Airplane ON → Wait 5s → Airplane OFF → Wait 10s → HTTP Response `200 OK`

See full guides:
- [MacroDroid Airplane Toggle](macrodroid_airplane.md)
- [MacroDroid + AutoInput Setup](droid_ui/setup_guide.md)

## How It Works

```
User clicks PPC link (arolinks/vplink)
  ↓
ppccli opens it in Chromium (mobile emulation)
  ↓
Hop loop (up to 45 hops per view):
  ├─ hittracks.in.net → click_image, timer, scroll_continue
  ├─ krishitalk.com → click_ads, get_link
  ├─ arolinks.com / vplink.in → timer, telegram, get_link
  └─ Destination URL found → SUCCESS
```

The script:
- Spoofs mobile fingerprints (Pixel 7/8/9, Galaxy S23/S24/S25, random WebGL renderers)
- Handles timers, captchas, overlays, interstitials
- Detects stuck pages and retries
- Supports 2 workers in parallel with separate Xvfb displays

## Requirements

| Dependency | Purpose |
|-----------|---------|
| **Python 3.8+** | Script runtime |
| **Chromium** | Headless browser |
| **Chromedriver** | Selenium WebDriver |
| **Xvfb** | Virtual framebuffer (headless display) |
| **x11vnc** | VNC server (optional, for debugging) |
| **selenium** | Python browser automation |
| **MacroDroid** (Android) | IP rotation via airplane mode toggle |

All installed automatically by `setup.sh`.

## Project Structure

```
ppccli/
├── ppccli.py                  # Main script (single file, ~1600 lines)
├── setup.sh                   # One-command installer
├── README.md                  # This file
├── FEATURES.md                # Full feature documentation
├── macrodroid_airplane.md     # MacroDroid airplane toggle guide
└── droid_ui/
    ├── macrodroid_ui.py       # Android automation Python module
    ├── setup_guide.md         # MacroDroid + AutoInput full setup guide
    └── example.py             # Example: automate WhatsApp
```

## License

MIT
