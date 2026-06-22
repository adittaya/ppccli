#!/usr/bin/env python3
"""
Example: automate WhatsApp using droid_ui.
Requires MacroDroid + AutoInput macros to be set up first.

Usage:
    python3 example.py
"""

import sys, time
from macrodroid_ui import Device

d = Device(port=8580)  # match your MacroDroid HTTP port

def main():
    print("1. Opening WhatsApp...")
    d.open_app("com.whatsapp")

    d.wait(3)

    print("2. Tapping search icon...")
    d.click_id("com.whatsapp:id/menuitem_search")

    d.wait(1)

    print("3. Typing contact name...")
    d.type_text("John")

    d.wait(2)

    print("4. Tapping contact...")
    d.click_text("John")

    d.wait(1)

    print("5. Typing message...")
    d.type_text("Hello from droid_ui!")

    d.wait(1)

    print("6. Sending...")
    d.click_id("com.whatsapp:id/send")

    print("Done!")

if __name__ == "__main__":
    main()
