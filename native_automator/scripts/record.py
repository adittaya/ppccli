#!/usr/bin/env python3
"""
Interactive element selector recorder.
Opens an app, shows its UI hierarchy, and helps you build selectors.

Usage:
    python3 scripts/record.py com.whatsapp
"""

import sys, time
sys.path.insert(0, "..")
from automator import Device, By

def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else input("Package name: ").strip()
    d = Device(port=8580)

    print(f"\nOpening {pkg}...")
    d.open_app(pkg)
    d.wait(3)

    print("\n" + "="*50)
    print("  Selector Recorder")
    print("="*50)
    print("\nCommands:")
    print("  t <text>       → test click by text")
    print("  i <id>         → test click by ID")
    print("  x <xpath>      → test click by XPath")
    print("  c <x> <y>      → test click by coordinates")
    print("  s              → take screenshot")
    print("  q              → quit")
    print()

    try:
        while True:
            cmd = input("> ").strip().split()
            if not cmd:
                continue
            if cmd[0] == "q":
                break
            elif cmd[0] == "t" and len(cmd) >= 2:
                text = " ".join(cmd[1:])
                print(f"  Clicking text: '{text}'")
                try:
                    d.click_text(text)
                    print(f"  [OK] Clicked")
                except Exception as e:
                    print(f"  [FAIL] {e}")
            elif cmd[0] == "i" and len(cmd) >= 2:
                rid = cmd[1]
                print(f"  Clicking ID: {rid}")
                try:
                    d.click_id(rid)
                    print(f"  [OK] Clicked")
                except Exception as e:
                    print(f"  [FAIL] {e}")
            elif cmd[0] == "x" and len(cmd) >= 2:
                xp = " ".join(cmd[1:])
                print(f"  Clicking XPath: {xp}")
                try:
                    d.click_xpath(xp)
                    print(f"  [OK] Clicked")
                except Exception as e:
                    print(f"  [FAIL] {e}")
            elif cmd[0] == "c" and len(cmd) >= 3:
                x, y = int(cmd[1]), int(cmd[2])
                print(f"  Clicking ({x}, {y})")
                try:
                    d.click_coord(x, y)
                    print(f"  [OK] Clicked")
                except Exception as e:
                    print(f"  [FAIL] {e}")
            elif cmd[0] == "s":
                d.screenshot()
                print("  Screenshot saved to /sdcard/automator_screen.png")
            else:
                print("  Unknown command")
    except KeyboardInterrupt:
        print("\n  Bye!")

if __name__ == "__main__":
    main()
