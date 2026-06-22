# Setup Guide: MacroDroid + AutoInput for UI Automation

This guide walks you through creating macros in MacroDroid so your Python
scripts can control any Android app by sending HTTP requests to localhost.

## Requirements

- [MacroDroid](https://play.google.com/store/apps/details?id=com.arlosoft.macrodroid) (installed)
- [AutoInput](https://play.google.com/store/apps/details?id=com.joaomgcd.autoinput) plugin (installed)
- Both apps need Accessibility Service enabled

## Step 1: Enable Accessibility for both apps

1. Settings → Accessibility → Installed apps
2. Enable **MacroDroid** accessibility
3. Enable **AutoInput** accessibility

## Step 2: Enable MacroDroid HTTP Server

1. Open MacroDroid
2. Tap the **3-dot menu** → **Settings**
3. Scroll to **HTTP Server** → enable it
4. Note the **port number** (default: `8580`)
5. Make sure **Allow any IP** or **Localhost only** is set (we use localhost)

## Step 3: Create the macros

For each UI action below, create a new macro in MacroDroid:

### 3a: Click by Text (`/click/text`)

1. **+ New Macro** → name: `Click Text`
2. **Trigger** → **Local HTTP Server** → URL Path: `/click/text`
3. **Constraint** (optional) → **Method**: `GET`
4. **Action** → **AutoInput** → **Action Type**: `Click`
   - **Find By**: `Text`
   - **Text (Variable)**: `[lv=http_q]`
5. Save

### 3b: Click by ID (`/click/id`)

1. **+ New Macro** → name: `Click ID`
2. **Trigger** → **Local HTTP Server** → URL Path: `/click/id`
3. **Action** → **AutoInput** → **Action Type**: `Click`
   - **Find By**: `ID`
   - **ID (Variable)**: `[lv=http_id]`
4. Save

### 3c: Click Coordinate (`/click/coord`)

1. **+ New Macro** → name: `Click Coord`
2. **Trigger** → **Local HTTP Server** → URL Path: `/click/coord`
3. **Action** → **AutoInput** → **Action Type**: `Click`
   - **Find By**: `Coordinates`
   - **X (Variable)**: `[lv=http_x]`
   - **Y (Variable)**: `[lv=http_y]`
4. Save

### 3d: Type Text (`/input/text`)

1. **+ New Macro** → name: `Type Text`
2. **Trigger** → **Local HTTP Server** → URL Path: `/input/text`
3. **Action** → **AutoInput** → **Action Type**: `Input Text`
   - **Text (Variable)**: `[lv=http_text]`
4. Save

### 3e: Swipe (`/swipe`)

1. **+ New Macro** → name: `Swipe`
2. **Trigger** → **Local HTTP Server** → URL Path: `/swipe`
3. **Action** → **AutoInput** → **Action Type**: `Swipe`
   - **Start X (Variable)**: `[lv=http_x1]`
   - **Start Y (Variable)**: `[lv=http_y1]`
   - **End X (Variable)**: `[lv=http_x2]`
   - **End Y (Variable)**: `[lv=http_y2]`
   - **Duration (Variable)**: `[lv=http_duration]` (default: 300ms)
4. Save

### 3f: Back Button (`/back`)

1. **+ New Macro** → name: `Back`
2. **Trigger** → **Local HTTP Server** → URL Path: `/back`
3. **Action** → **AutoInput** → **Action Type**: `System Button`
   - **Button**: `Back`
4. Save

### 3g: Home Button (`/home`)

1. **+ New Macro** → name: `Home`
2. **Trigger** → **Local HTTP Server** → URL Path: `/home`
3. **Action** → **AutoInput** → **System Button** → `Home`
4. Save

### 3h: Open App (`/app/open`)

1. **+ New Macro** → name: `Open App`
2. **Trigger** → **Local HTTP Server** → URL Path: `/app/open`
3. **Action** → **App** → **Open App**
   - **Package**: `[lv=http_package]`
4. Save

### 3i: Scroll Down (`/scroll/down`)

1. **+ New Macro** → name: `Scroll Down`
2. **Trigger** → **Local HTTP Server** → URL Path: `/scroll/down`
3. **Action** → **AutoInput** → **Action Type**: `Swipe`
   - **Start X**: `540`, **Start Y**: `1500`
   - **End X**: `540`, **End Y**: `400`
   - **Duration**: `300`
4. Save

### 3j: Screenshot (`/screenshot`)

1. **+ New Macro** → name: `Screenshot`
2. **Trigger** → **Local HTTP Server** → URL Path: `/screenshot`
3. **Action** → **AutoInput** → **Action Type**: `Take Screenshot`
   (or use MacroDroid's built-in Screenshot action)
4. Save

### 3k: Text Exists (`/text/exists`)

1. **+ New Macro** → name: `Text Exists`
2. **Trigger** → **Local HTTP Server** → URL Path: `/text/exists`
3. **Action** → **MacroDroid** → **Set Variable**
   - **Variable**: `text_found` (local)
   - **Value**: `false`
4. **Action** → **AutoInput** → **Action Type**: `Wait For Element`
   - **Find By**: `Text` → **Text**: `[lv=http_q]`
   - **Timeout**: `1` second
5. **Action** → **MacroDroid** → **Set Variable**
   - **Variable**: `text_found`
   - **Value**: `true` (only if step 4 succeeded)
6. **Action** → **Networking** → **HTTP Response**
   - **Response Code**: `200`
   - **Content Type**: `application/json`
   - **Content**: `{"found": true}` or `{"found": false}`

## Step 4: Test the macros

Once all macros are created, test from Termux:

```bash
# Test text click
curl "http://127.0.0.1:8580/click/text?q=Settings"

# Test type text
curl "http://127.0.0.1:8580/input/text?text=hello"

# Test back button
curl "http://127.0.0.1:8580/back"

# Test open app
curl "http://127.0.0.1:8580/app/open?package=com.whatsapp"
```

## Step 5: Use the Python module

```python
from droid_ui import Device

d = Device(port=8580)  # same port as your HTTP server
d.open_app("com.whatsapp")
d.click_text("Search")
d.type_text("hello")
d.back()
```

## URL Parameter Reference

| Macro Endpoint | Query Params | Example |
|---|---|---|
| `/click/text` | `q` (text to find) | `/click/text?q=Login` |
| `/click/id` | `id` (resource ID) | `/click/id?id=com.app:id/btn` |
| `/click/coord` | `x`, `y` | `/click/coord?x=500&y=1000` |
| `/input/text` | `text` | `/input/text?text=hello` |
| `/swipe` | `x1`, `y1`, `x2`, `y2`, `duration` | `/swipe?x1=300&y1=900&x2=300&y2=300` |
| `/app/open` | `package`, `activity` | `/app/open?package=com.whatsapp` |

## Finding Element IDs

To find the resource ID of an element you want to click:

**Method A — UI Automator Viewer (desktop)**:
1. Run from laptop: `adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml`
2. Open `ui.xml` in a browser — search for your element's text, find its `resource-id`

**Method B — AutoInput UI Query (on-device)**:
1. Open MacroDroid
2. **+ New Action** → **AutoInput** → **UI Query**
3. Run it — it shows the current UI hierarchy with IDs
4. Delete the action when done

## Notes

- All macros run via MacroDroid's Accessibility Service — no root needed
- The automation runs in the background; you can use your phone freely
- If a macro doesn't trigger, check:
  - MacroDroid HTTP server is ON (Settings → HTTP Server)
  - Accessibility Service is enabled for Macrodroid and AutoInput
  - The URL path matches EXACTLY (capitalization matters: `/click/text` not `/Click/Text`)
- Each macro takes ~0.5-2 seconds to execute (Accessibility Service latency)
