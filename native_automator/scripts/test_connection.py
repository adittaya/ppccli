#!/usr/bin/env python3
"""Test MacroDroid HTTP connection and list available macros."""

import sys, urllib.request, json

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = sys.argv[2] if len(sys.argv) > 2 else "8580"

print(f"Testing MacroDroid HTTP server at {HOST}:{PORT}...")
try:
    r = urllib.request.urlopen(f"http://{HOST}:{PORT}/", timeout=5)
    print(f"  [✓] Server reachable (HTTP {r.getcode()})")
except urllib.error.URLError as e:
    print(f"  [✗] Cannot connect: {e.reason}")
    print()
    print("Troubleshooting:")
    print("  1. Open MacroDroid → Settings → HTTP Server → enable it")
    print("  2. Verify the port number (default: 8580)")
    print("  3. Make sure both devices are on the same network (if not localhost)")
    sys.exit(1)

# Test each macro endpoint
ENDPOINTS = [
    "/click/text?q=test",
    "/click/id?id=test",
    "/back",
    "/home",
    "/app/open?package=com.android.settings",
    "/swipe?x1=100&y1=100&x2=200&y2=200",
    "/input/text?text=hello",
]

print("\nTesting macro endpoints:")
for ep in ENDPOINTS:
    path = ep.split("?")[0]
    try:
        r = urllib.request.urlopen(f"http://{HOST}:{PORT}{ep}", timeout=3)
        print(f"  [{r.getcode()}] {path}")
    except urllib.error.HTTPError as e:
        code = e.code
        icon = " " if code == 404 else "?"
        print(f"  [{code}]{icon} {path}  {'→ create this macro in MacroDroid' if code == 404 else ''}")
    except Exception as e:
        print(f"  [!] {path}  → {e}")

print("\nDone.")
