#!/usr/bin/env python3
"""
YouTube automation example using native_automator.

Demonstrates: open YouTube, search, scroll, like, comment.

Setup: MacroDroid macros must be created first (run setup_macros.py).
"""

import sys, time
sys.path.insert(0, "..")
from automator import Device, By

d = Device(port=8580)

def main():
    print("1. Opening YouTube...")
    d.open_app("com.google.android.youtube")
    d.wait(5)

    print("2. Searching...")
    d.click_id("com.google.android.youtube:id/search_icon")
    d.wait(1)
    d.type_text("python automation")
    d.wait(1)
    # Press Enter / search key
    d.click_id("com.google.android.youtube:id/search_edit_text")
    d.wait(3)

    print("3. Scrolling results...")
    d.scroll_down()
    d.wait(1)
    d.scroll_down()

    print("4. Clicking first video...")
    d.click_id("com.google.android.youtube:id/title")
    d.wait(5)

    print("5. Liking video...")
    d.click_id("com.google.android.youtube:id/like_button")
    d.wait(1)

    print("Done! YouTube automation complete.")

if __name__ == "__main__":
    main()
