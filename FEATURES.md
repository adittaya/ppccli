# PPCCLI — Feature Summary

> Final unified PPC page flow navigator. Merges ppc-universal (multi-network) + fastppc (VPLINK-optimized) + new improvements. Supports VPLINK and LinkPays networks.

## Core

- **Universal PPC support**: VPLINK (`hittracks` → `krishitalk` → `vplink` → destination), AroLinks (`arolinks.com`, same hittracks cycle), LinkPays (`savepe.in`, `rank1st.in`, `roadtaxcalculator`, `bookyourhotel`), and other PPC/shortener networks — auto-detected from URL domain
- **Single-file script** (`ppccli.py`) — zero dependencies beyond Selenium + Chromium
- **Three modes**: single (one URL, one Chrome), parallel (`-p` / `--parallel`), interactive CLI (`-i` / no args)
- **Symlinked CLI command** at `/usr/local/bin/ppccli` → instantly picks up repo edits
- **Parallel mode**: multi-window, multi-URL, multi-session orchestrator with session summary

## Navigation Flow

- **10 action types**: `verify`, `click_ads`, `unlock`, `timer`, `get_link`, `scroll_continue`, `click_image`, `step2`, `not_interested`, `telegram` — parsed from page text each hop
- **45-hop max loop** per view — aborts earlier if destination found
- **Gateway handler**: clicks "Continue to Next" on entry pages (first 3 hops)
- **`#goog_rewarded` interstitial handler**: scrolls, clicks Continue/Skip/Close, breaks early when found
- **MSC/Doubleclick/Google ad pages**: auto-accept consent, close extra tabs, skip

## Get Link Strategy (multi-layered)

1. **Native click** (`click_any_native`) — uses Selenium WebDriver element click (trusted event)
2. **Bottom-up JS click** (`click_any`) — scans visible elements from bottom of DOM upward
3. **Popup detection** — compares tab count pre/post click; polls new tab URL for 10s
4. **Direct navigation fallback** — scans `<a>` elements bottom-up for "get link" href, then `p.get(hrefs)` to bypass JS interceptors
5. **`skip_ppc_check` flag** — after successful get-link, does NOT filter destination by PPC indicators (avoids false-positive on the real destination page)

## Timer

- Parses wait duration from page text (`wait 12 sec`, `10 sec link generating`, `linkpays 12 sec`)
- Defaults to 12s if no match
- **Polls body text every 2s** for "get link", "download", "your link", or "destination" — breaks early if found
- Adds 3s margin beyond advertised duration

## IP Rotation

- **Full visibility**: prints `[IP] Current`, `[IP] Airplane ON`, `[IP] Airplane OFF`, `[IP] Network OK`, `[IP] New: X | Changed: YES/NO` on every rotation
- **MacroDroid HTTP API** at `http://127.0.0.1:8080/rotate_ip` (toggle airplane mode)
- **Lock file** (`/tmp/ppccli_ip_rotate`) prevents concurrent rotations
- **Stale lock cleanup**: auto-removes locks older than 300 seconds (from crashed runs)
- **Returns `changed` bool** — tells the caller whether the IP actually changed
- **Smart retry**: retry only rotates IP if the **first** rotation failed (no double-waste)

## Abort / Recovery

- **Chrome-error abort**: 3 consecutive `chrome-error://chromewebdata/` hops → view aborted with `False`
- **Stuck abort**: 8 consecutive same-URL hops → force-scroll + force-click "Get Link" + force-DOM-scan; 3rd stuck occurrence → view aborted
- **View-level retry**: if `run_view()` returns `False`, one retry with fresh driver reset; rotates IP only if first rotation failed
- **Driver crash recovery**: 3 retries with new driver on `invalid session id` (Chrome process died)

## Fingerprint Variation

- **44 Android device models** (Pixel 7/8/9, Galaxy S23/S24/S25, Moto G, OnePlus 12/11, Xiaomi 14/13T, Redmi Note)
- **12 WebGL renderers** (Adreno, Mali variants)
- **Canvas fingerprint noise** — random pixel perturbation in `toDataURL`
- **WebGL vendor spoofing** (Qualcomm, Google, ARM, MediaTek, Samsung)
- **Timezone override** — random offset from -600 to +720 minutes
- **`hardwareConcurrency`** spoof (2/4/6/8 cores)
- **`deviceMemory`** spoof (1/2/4/6/8 GB)
- **Random User-Agent** with Android version + device model + Chrome version
- **CDP `Emulation.setDeviceMetricsOverride`** — mobile viewport, touch events, random scale factor
- **Per-execution random profile dir** (`/tmp/ppccli_XXXXX`) — fresh Chrome profile each driver

## Tab & Overlay Management

- **`nuke_overlays()`**: removes fixed/sticky elements with z-index > 1000, auto-dismisses close buttons (`×`, `✕`), suppresses `alert`/`confirm`/`prompt`
- **`close_extra_tabs()`**: closes all tabs except main handle
- **Multi-tab destination scan**: checks every open tab for non-PPC destination (body > 50 chars)
- **`reset_driver()`**: clears localStorage, sessionStorage, cookies, cache; navigates to about:blank

## Parallel Mode

- **`-p` / `--parallel` flag** — enables multi-window parallel execution
- **Interactive parallel prompt** (`ppccli -i` → choose "p"): enter URLs for VPLINK/AroLinks, LinkPays, Custom + unlimited extras
- **CLI parallel** (`ppccli -p URL1 URL2 URL3 -w 2`): each URL gets `-w` windows
- **Each worker gets its own display** (`:99`, `:100`, `:101`, ...) with independent Xvfb
- **Each worker gets its own VNC port** (`5900`, `5901`, `5902`, ...) when VNC enabled
- **Session-based**: IP rotates once before each session, then ALL workers start simultaneously
- **Session summary**: after every session, shows success/fail per worker + percentage
- **Early exit**: if any worker succeeds in a session, the orchestrator stops
- **All-session retry**: if all workers fail in a session, rotates IP and retries up to `-n` sessions

## Display

- **Xvfb auto-start** on `:99` (1366×900×24) — auto-restarts on crash
- **VNC optional** (`--no-vnc` flag / interactive toggle) — skips x11vnc launch, saves ~50MB RAM, no port conflicts for parallel runs
- **Chrome window position** controllable via `WIN_X` / `WIN_Y` env vars

## Configuration

| CLI flag | Interactive Q | Default | Purpose |
|---|---|---|---|---|
| `-i` | (auto if no URL) | — | Interactive mode |
| `-p` | (s)ingle or (p)arallel | single | Parallel multi-window mode |
| `-n N` | Number of views/sessions | 1 | Total views (single) or sessions (parallel) |
| `-w N` | Windows per URL | 1 | Chrome instances per URL in parallel mode |
| `--no-rotate` | Rotate IP? | No | Skip IP rotation |
| `-r URL` | YouTube referrer? | None | Referrer for navigation |
| `--no-vnc` | Start VNC? | No | Skip VNC server(s) |
| `URL` | PPC URL(s) | (required) | Target PPC link(s) |

## Destination Detection

- Domain-based exclusion against known PPC/ads/social domains
- Page body must have > 50 characters of text (not just a blank/excluded URL)
- PPC indicator re-check: if destination URL domain is unknown but page text contains PPC keywords, domain is added to exclusion list and loop continues
- Fallback DOM scan (`find_dest_in_page`): scans all `<a href>` for non-excluded URLs and navigates directly

## Supported Networks / Domains

| Network | Domains |
|---|---|
| **LinkPays** | `savepe.in`, `rank1st.in`, `roadtaxcalculator.`, `roadtaxcalculatorr.`, `bookyourhotel.` |
| **VPLINK / AroLinks** | `hittracks.`, `krishitalk.`, `vplink.`, `arolinks.` |
| **Ad / shortener** | `adsterra.`, `trafficbalance.`, `adspaces.`, `adshrink.`, `shortlink.`, `shortener.`, `shorte.`, `shrinkme.`, `tinyurl.`, `bitly.` |

Auto-excluded from destination detection. The flow continues hopping through these domains until a non-excluded domain is found.

## Safety Nets

- `page_load_strategy = "none"` + 8s page load timeout → never hangs on slow pages
- `set_script_timeout(6)` — JS execution capped at 6s
- `implicitly_wait(3)` — element waits capped at 3s
- Dismiss all dialogs at start of each hop
- Check all tabs for destination after every action
- YouTube referrer header via CDP `Page.navigate` with `referrer` param
- `/proc/net/*` permission errors caught and ignored (container sandbox — non-fatal)
