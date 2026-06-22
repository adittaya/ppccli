#!/usr/bin/env python3
"""
Interactive MacroDroid macro setup guide.
Run this script — it prints each macro definition one at a time.
Press Enter to advance to the next one.
"""

import sys

MACROS = [
    {
        "name": "Click Text",
        "endpoint": "/click/text",
        "params": "?q=<text>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /click/text",
            "2. Action → AutoInput → Action Type: Click",
            "   Find By: Text",
            "   Text (Variable): [lv=http_q]",
        ],
    },
    {
        "name": "Click ID",
        "endpoint": "/click/id",
        "params": "?id=<resource_id>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /click/id",
            "2. Action → AutoInput → Action Type: Click",
            "   Find By: ID",
            "   ID (Variable): [lv=http_id]",
        ],
    },
    {
        "name": "Click XPath",
        "endpoint": "/click/xpath",
        "params": "?xpath=<xpath_expression>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /click/xpath",
            "2. Action → AutoInput → Action Type: Click",
            "   Find By: XPath",
            "   Expression (Variable): [lv=http_xpath]",
        ],
    },
    {
        "name": "Click Coordinate",
        "endpoint": "/click/coord",
        "params": "?x=<x>&y=<y>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /click/coord",
            "2. Action → AutoInput → Action Type: Click",
            "   Find By: Coordinates",
            "   X (Variable): [lv=http_x]",
            "   Y (Variable): [lv=http_y]",
        ],
    },
    {
        "name": "Type Text",
        "endpoint": "/input/text",
        "params": "?text=<string>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /input/text",
            "2. Action → AutoInput → Action Type: Input Text",
            "   Text (Variable): [lv=http_text]",
        ],
    },
    {
        "name": "Swipe",
        "endpoint": "/swipe",
        "params": "?x1=<x>&y1=<y>&x2=<x>&y2=<y>&duration=<ms>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /swipe",
            "2. Action → AutoInput → Action Type: Swipe",
            "   Start X (Variable): [lv=http_x1]",
            "   Start Y (Variable): [lv=http_y1]",
            "   End X (Variable): [lv=http_x2]",
            "   End Y (Variable): [lv=http_y2]",
            "   Duration (Variable): [lv=http_duration]",
        ],
    },
    {
        "name": "Back Button",
        "endpoint": "/back",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /back",
            "2. Action → AutoInput → System Button → Back",
        ],
    },
    {
        "name": "Home Button",
        "endpoint": "/home",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /home",
            "2. Action → AutoInput → System Button → Home",
        ],
    },
    {
        "name": "Recent Apps",
        "endpoint": "/recent",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /recent",
            "2. Action → AutoInput → System Button → Recent Apps",
        ],
    },
    {
        "name": "Open App",
        "endpoint": "/app/open",
        "params": "?package=<pkg_name>&activity=<optional>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /app/open",
            "2. Action → App → Open App",
            "   Package (Variable): [lv=http_package]",
        ],
    },
    {
        "name": "Kill App",
        "endpoint": "/app/kill",
        "params": "?package=<pkg_name>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /app/kill",
            "2. Action → App → Force Stop App",
            "   Package (Variable): [lv=http_package]",
        ],
    },
    {
        "name": "Text Exists",
        "endpoint": "/text/exists",
        "params": "?q=<text>&timeout=<seconds>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /text/exists",
            "2. Action → AutoInput → UI Query",
            "3. Action → MacroDroid → Set Variable → 'found' = true/false",
            "4. Action → Networking → HTTP Response",
            "   Code: 200",
            "   Content: {\"found\": true} or {\"found\": false}",
        ],
    },
    {
        "name": "Screenshot",
        "endpoint": "/screenshot",
        "params": "?path=<file_path>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /screenshot",
            "2. Action → MacroDroid → Take Screenshot",
            "   Save to (Variable): [lv=http_path]",
        ],
    },
    {
        "name": "Screen On",
        "endpoint": "/screen/on",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /screen/on",
            "2. Action → MacroDroid → Device → Screen On",
        ],
    },
    {
        "name": "Screen Off",
        "endpoint": "/screen/off",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /screen/off",
            "2. Action → MacroDroid → Device → Lock Screen",
        ],
    },
    {
        "name": "Volume Up",
        "endpoint": "/volume/up",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /volume/up",
            "2. Action → MacroDroid → Volume → Volume Up",
        ],
    },
    {
        "name": "Volume Down",
        "endpoint": "/volume/down",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /volume/down",
            "2. Action → MacroDroid → Volume → Volume Down",
        ],
    },
    {
        "name": "Notification",
        "endpoint": "/notification",
        "params": "?title=<t>&text=<t>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /notification",
            "2. Action → MacroDroid → Notification → Post Notification",
            "   Title (Variable): [lv=http_title]",
            "   Text (Variable): [lv=http_text]",
        ],
    },
    {
        "name": "Clipboard Get",
        "endpoint": "/clipboard/get",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /clipboard/get",
            "2. Action → MacroDroid → Set Variable → 'text' = Clipboard contents",
            "3. Action → Networking → HTTP Response: {\"text\": \"[text]\"}",
        ],
    },
    {
        "name": "Clipboard Set",
        "endpoint": "/clipboard/set",
        "params": "?text=<string>",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /clipboard/set",
            "2. Action → MacroDroid → Clipboard → Set Clipboard",
            "   Text (Variable): [lv=http_text]",
        ],
    },
    {
        "name": "Screen Locked Check",
        "endpoint": "/screen/locked",
        "params": "(none)",
        "macro": [
            "1. Trigger → Local HTTP Server → URL: /screen/locked",
            "2. Action → MacroDroid → Set Variable → 'locked' = true/false",
            "3. Action → Networking → HTTP Response: {\"locked\": true}",
        ],
    },
]


def print_macro(m, index, total):
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  Macro {index}/{total}: {m['name']}")
    print(f"  Endpoint:  {m['endpoint']}")
    print(f"  Params:    {m['params']}")
    print(f"{sep}")
    for line in m["macro"]:
        print(f"  {line}")
    print(f"{sep}")
    print(f"  Open MacroDroid → + New Macro → name: {m['name']}")
    print(f"  Then follow the steps above.")
    print()


def main():
    total = len(MACROS)
    print(f"\n  {'='*50}")
    print(f"  native_automator — MacroDroid Macro Setup")
    print(f"  {'='*50}")
    print(f"\n  You need to create {total} macros in MacroDroid.")
    print(f"  Each macro = 1 HTTP endpoint + 1 AutoInput action.")
    print(f"  Estimated time: 20-30 minutes.")
    print(f"\n  Press Enter to start, or Ctrl+C to quit.")
    input()

    for i, m in enumerate(MACROS, 1):
        print_macro(m, i, total)
        if i < total:
            input("  [Press Enter for next macro...]")
        else:
            print("  [Last macro. Press Enter to finish.]")
            input()

    print(f"\n  All {total} macros defined!")
    print(f"\n  Next steps:")
    print(f"  1. Enable MacroDroid Accessibility Service")
    print(f"  2. Enable AutoInput Accessibility Service")
    print(f"  3. Enable MacroDroid HTTP Server (Settings → HTTP Server)")
    print(f"  4. Run: python3 scripts/test_connection.py")
    print(f"  5. Start automating!")


if __name__ == "__main__":
    main()
