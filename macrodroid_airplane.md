# MacroDroid Airplane Toggle for IP Rotation

This guide creates a MacroDroid macro that toggles airplane mode via HTTP request.
`ppccli` calls this macro automatically between sessions to rotate your IP address.

## Requirements

- [MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) installed
- Android device (phone / tablet) on the same network **or** connected via USB reverse tether
- Termux or ADB to test

## Step 1: Enable MacroDroid HTTP Server

1. Open MacroDroid
2. Tap the **3-dot menu** (⋮) → **Settings**
3. Scroll to **HTTP Server** → enable it
4. Note the **port number** (default is `8580` — we'll use `8080`)
   - Tap **Port** → change to `8080`
5. Set **Allow any IP** or **Localhost only** (use `Localhost only` if running ppccli on the same device)

## Step 2: Create the Airplane Toggle Macro

1. **+ New Macro** → name it: `Rotate IP`
2. **Trigger** → **Local HTTP Server**:
   - URL Path: `/rotate_ip`
   - Method: `GET`
3. **Action 1** → **Connectivity** → **Airplane Mode** → **Enable**
4. **Action 2** → **Variables** → **Wait** → `5` seconds
5. **Action 3** → **Connectivity** → **Airplane Mode** → **Disable**
6. **Action 4** → **Variables** → **Wait** → `10` seconds *(lets network reconnect)*
7. **Action 5** → **Networking** → **HTTP Response**:
   - Response Code: `200`
   - Content Type: `text/plain`
   - Content: `OK`
8. **Save** the macro

Optional — add notification so you can see when it runs:
- **Action 0** (at the top): **Alerts** → **Display Notification**
  - Title: `IP Rotation`
  - Content: `Toggling airplane mode...`

## Step 3: Get your device IP

Run this in Termux to find the device's local IP:

```bash
ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+'
```

Or check: **Settings** → **About phone** → **Status** → **IP address**

## Step 4: Test the macro

```bash
# From the same device (localhost):
curl -s "http://127.0.0.1:8080/rotate_ip"

# From another machine on the same network:
curl -s "http://<DEVICE_IP>:8080/rotate_ip"
```

Expected output: `OK` (after the phone toggles airplane mode and reconnects)

## Step 5: Wire it into ppccli

ppccli already calls `http://127.0.0.1:8080/rotate_ip` by default (see `rotate_ip()` in `ppccli.py`).

If the device IP is different (e.g. `192.168.1.100`), set the environment variable:

```bash
export MACRODROID_URL="http://192.168.1.100:8080/rotate_ip"
```

Or edit the `macrodroid` list in `ppccli.py:786`:

```python
macrodroid = ["http://192.168.1.100:8080/rotate_ip", "http://127.0.0.1:8080/rotate_ip"]
```

## Step 6: Running on the same device (Termux)

If you run ppccli directly on your Android phone via Termux:

1. Install Termux from F-Droid
2. Install packages: `pkg install python chromium chromedriver xvfb-run`
3. Clone the repo: `git clone https://github.com/adittaya/ppccli`
4. Run setup: `cd ppccli && bash setup.sh`
5. MacroDroid listens on `127.0.0.1:8080` — no network config needed

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `[IP] MacroDroid unreachable` | Ensure HTTP Server is ON in MacroDroid Settings |
| `Connection refused` | Check the port matches (8080) and IP is correct |
| `404 Not Found` | Macro name must be exactly `Rotate IP`, trigger URL path exactly `/rotate_ip` |
| IP unchanged after toggle | Increase wait times in the macro (steps 2 and 4) — your carrier may take longer to assign a new IP |
| No new IP available | Some carriers (especially CGNAT) don't give a new IP on reconnect. Use a VPN or proxy instead (`--no-rotate`) |
