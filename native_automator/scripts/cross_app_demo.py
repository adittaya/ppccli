#!/usr/bin/env python3
"""
Advanced example: cross-app automation.
Opens Settings → turns on DND → opens WhatsApp → sends message → opens YouTube → searches.
"""

import sys, time
sys.path.insert(0, "..")
from automator import Device, By, Gestures

d = Device(port=8580)

def main():
    # ── Step 1: Open Settings, toggle DND ──
    print("1. Opening Settings → Do Not Disturb...")
    d.open_app("com.android.settings")
    d.wait(3)
    d.click_text("Do Not Disturb")
    d.wait(2)
    d.click_text("Turn on now")
    d.wait(1)
    d.back()
    d.wait(1)

    # ── Step 2: Open WhatsApp ──
    print("2. Opening WhatsApp...")
    d.open_app("com.whatsapp")
    d.wait(4)

    # Check if we're on the chat list
    if d.text_exists("Search", timeout=2):
        print("   WhatsApp loaded successfully")
        d.click_text("Search")
        d.wait(1)
        d.type_text("Test Contact")
        d.wait(2)
        d.click_text("Test Contact")
        d.wait(2)
        d.type_text("Hello from native_automator!")
        d.wait(1)
        d.click_id("com.whatsapp:id/send")
        print("   Message sent!")
    else:
        print("   WhatsApp didn't load in time, continuing...")

    d.home()
    d.wait(1)

    # ── Step 3: Open YouTube ──
    print("3. Opening YouTube...")
    d.open_app("com.google.android.youtube")
    d.wait(5)
    d.click_id("com.google.android.youtube:id/search_icon")
    d.wait(1)
    d.type_text_slow("android automation", delay_ms=60)
    d.wait(2)

    # Scroll
    for _ in range(3):
        d.scroll_down()
        d.wait(1)

    print("4. Done! All cross-app automation completed.")

if __name__ == "__main__":
    main()
