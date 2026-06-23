#!/usr/bin/env python3
"""
ppccli — Universal PPC page flow navigator.
Handles: VPLINK (hittracks → krishitalk → vplink → destination),
AroLinks (arolinks.com, same hittracks cycle),
LinkPays (savepe.in, rank1st.in, roadtaxcalculator, bookyourhotel),
and other PPC networks. Single-process, quality-focused, final version.
"""
import os, sys, time, re, random, subprocess, threading, multiprocessing, urllib.request, glob
from urllib.parse import urlparse
from collections import OrderedDict

os.environ.setdefault("DISPLAY", ":99")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
except ImportError:
    print("Run: pip install selenium")
    sys.exit(1)

# Display & VNC are read dynamically from os.environ in ensure_display()
# and make_driver() to support parallel workers each with their own display.

PPC_DOMAINS = [
    # LinkPays
    "linkpays.", "savepe.in", "rank1st.in", "roadtaxcalculator.", "roadtaxcalculatorr.",
    "bookyourhotel.",
    # VPLINK / AroLinks
    "hittracks.", "krishitalk.", "vplink.", "arolinks.",
    # Ad / shortener
    "adsterra.", "trafficbalance.", "adspaces.", "adshrink.",
    "shortlink.", "shortener.", "shorte.", "shrinkme.", "tinyurl.", "bitly.",
]
EX_DOMAINS = PPC_DOMAINS + [
    "about:blank", "msc", "doubleclick", "google", "facebook", "instagram",
    "youtube", "chrome-error", "chromewebdata"
]
SOCIAL_DOMAINS = ["wa.me", "api.whatsapp.com", "facebook.com/share", "twitter.com/intent",
                  "x.com/intent", "linkedin.com/share", "t.me", "telegram.me"]

# PPC domain chain: when on a domain, the expected next hop in the flow
PPC_CHAIN = {
    "rank1st.in": ["savepe.in", "savepe."],
    "roadtaxcalculator.": ["savepe.in", "savepe."],
    "roadtaxcalculatorr.": ["savepe.in", "savepe."],
    "savepe.in": ["bookyourhotel."],
    "savepe.": ["bookyourhotel."],
    "hittracks.": ["krishitalk."],
    "krishitalk.": ["arolinks.", "vplink."],
}

ANDROID_VERSIONS = ["10","11","12","12.1","13","14","15"]
DEVICE_MODELS = [
    "Pixel 7","Pixel 7 Pro","Pixel 8","Pixel 8 Pro","Pixel 9",
    "SM-S908B","SM-S928B","SM-A536E","SM-A546E","SM-A156E",
    "moto g(7) power","moto g(8) plus","moto g(9) play",
    "OnePlus 12","OnePlus 11","OnePlus 10 Pro","OnePlus Nord 4",
    "Xiaomi 14","Xiaomi 13T","Redmi Note 13 Pro","Redmi Note 12",
    "Pixel 6","Pixel 6 Pro","SM-F946B","SM-F936B","SM-F721B",
    "moto g73 5G","moto g54 5G","moto g84 5G","OnePlus 10R",
    "OnePlus Nord CE 3","Xiaomi 12","Xiaomi 12T Pro","Redmi Note 11",
    "Redmi Note 10","POCO X5 Pro","POCO F5","vivo V29","vivo Y100",
    "Oppo Reno 10","Oppo F23","Realme 11 Pro","Realme Narzo 60",
]
ROTATE_LOCK = "/tmp/ppccli_ip_rotate"
MAIN_HANDLE = None

# Clean stale temp profiles and lock from crashed runs
try:
    for d in glob.glob("/tmp/ppccli_*"):
        if os.path.isdir(d):
            subprocess.run(f"rm -rf '{d}' 2>/dev/null", shell=True)
except: pass

# Clean stale lock from crashed runs
try:
    st = os.stat(ROTATE_LOCK)
    if time.time() - st.st_mtime > 300:
        os.rmdir(ROTATE_LOCK)
except (FileNotFoundError, OSError): pass

NUKE_JS = r"""
(function(){
  document.querySelectorAll('*').forEach(function(e){
    var p=getComputedStyle(e).position;
    var z=parseInt(getComputedStyle(e).zIndex)||0;
    if((p==='fixed'||p==='sticky')&&z>1000)e.remove();
    if(z>9999)e.remove();
  });
  document.body.style.overflow='auto';
  document.body.style.position='static';
  document.documentElement.style.overflow='auto';
})();
"""

PPC_INDICATORS = ["get link","download","verify","unlock","i'm not robot","not robot","gate link",
                  "please wait","scroll down","continue","next",
                  "link is generating","step 2/3","click any image"]

# ──────────────────────────────────────────────
# DISPLAY
# ──────────────────────────────────────────────
def ensure_display():
    display_num = int(os.environ.get("DISPLAY", ":99").lstrip(":"))
    vnc_port = int(os.environ.get("VNC_PORT", "5900"))
    no_vnc = os.environ.get("NO_VNC", "").lower() in ("1","true","yes")
    if not no_vnc:
        vnc_alive = subprocess.run(f"fuser {vnc_port}/tcp &>/dev/null", shell=True).returncode == 0
        if vnc_alive:
            return
    lock = f"/tmp/.X{display_num}-lock"
    restart = False
    if os.path.exists(lock):
        try:
            subprocess.run(["xdpyinfo","-display",f":{display_num}"], capture_output=True, timeout=3, check=True)
        except:
            os.remove(lock)
            restart = True
    if restart or not os.path.exists(lock):
        subprocess.run(f"pkill -9 -f 'Xvfb :{display_num}' 2>/dev/null", shell=True)
        time.sleep(0.5)
        subprocess.run(f"Xvfb :{display_num} -screen 0 1366x900x24 &>/dev/null &", shell=True)
        time.sleep(2)
    if no_vnc:
        return
    r = subprocess.run(f"fuser {vnc_port}/tcp &>/dev/null", shell=True)
    if r.returncode != 0:
        vnc_log = f"/tmp/x11vnc_{display_num}.log"
        subprocess.run(f"x11vnc -display :{display_num} -forever -shared -rfbport {vnc_port} -nopw -quiet -bg >{vnc_log} 2>&1", shell=True)
        time.sleep(2)
        alive = subprocess.run(f"fuser {vnc_port}/tcp &>/dev/null", shell=True).returncode == 0
        if not alive:
            print(f"  [VNC] x11vnc failed to start — check {vnc_log}", flush=True)
            subprocess.run(f"x11vnc -display :{display_num} -forever -shared -rfbport {vnc_port} -nopw -bg >{vnc_log} 2>&1", shell=True)
            time.sleep(2)

# ──────────────────────────────────────────────
# FINGERPRINT
# ──────────────────────────────────────────────
def random_ua():
    av = random.choice(ANDROID_VERSIONS)
    dv = random.choice(DEVICE_MODELS)
    cv = f"{random.randint(120,127)}.0.{random.randint(6000,6600)}.{random.randint(64,250)}"
    return f"Mozilla/5.0 (Linux; Android {av}; {dv}) AppleWebKit/534.36 (KHTML, like Gecko) Chrome/{cv} Mobile Safari/534.36"

def make_driver():
    time.sleep(random.uniform(1, 3))
    ensure_display()
    vw = 390 + random.randint(-30, 30)
    vh = 844 + random.randint(-30, 30)
    profile_dir = f"/tmp/ppccli_{random.randint(10000,99999)}"
    ua = random_ua()
    hw_cores = random.choice([2,4,6,8])
    dev_mem = random.choice([1,2,4,6,8])
    webgl_vendor = random.choice(["Qualcomm","Google","ARM","MediaTek","Samsung",
                                   "Apple","Intel"])
    webgl_renderer = random.choice([
        "Adreno (TM) 640","Adreno (TM) 730","Adreno (TM) 740","Adreno (TM) 750",
        "Mali-G76 MP4","Mali-G77 MP5","Mali-G78 MP14","Mali-G610 MP4",
        "Mali-G68 MP4","PowerVR GM9446","PowerVR GE8320","Adreno (TM) 660",
    ])
    tz = random.choice([-300,-360,-420,-480,-540,-600,60,120,180,240,330,345,420,480,540,570,660,720])
    o = Options()
    o.binary_location = "/usr/bin/chromium"
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--test-type")
    o.add_argument("--headless=old")
    o.add_argument("--disable-gpu")
    o.add_argument("--disable-software-rasterizer")
    o.add_argument("--disable-extensions")
    o.add_argument("--disable-background-networking")
    o.add_argument("--disable-background-timer-throttling")
    o.add_argument("--disable-renderer-backgrounding")
    o.add_argument("--disable-backgrounding-occluded-windows")
    o.add_argument("--memory-pressure-off")
    o.add_argument("--aggressive-cache-discard")
    o.add_argument("--disk-cache-size=1")
    o.add_argument("--js-flags=--max_old_space_size=256")
    o.add_argument("--renderer-process-limit=1")
    o.add_argument("--disable-sync")
    o.add_argument("--disable-translate")
    o.add_argument("--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies,OptimizationGuideModelDownloading,OptimizationHintsFetching")
    o.add_argument(f"--window-size={vw},{vh}")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_argument(f"--user-agent={ua}")
    o.add_argument(f"--user-data-dir={profile_dir}")
    win_x = os.environ.get("WIN_X")
    win_y = os.environ.get("WIN_Y")
    if win_x and win_y:
        o.add_argument(f"--window-position={win_x},{win_y}")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    o.page_load_strategy = "none"
    for attempt in range(5):
        try:
            d = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=o)
            break
        except Exception as e:
            if attempt < 4:
                ensure_display()
                time.sleep(3 + attempt * 3)
            else:
                raise e
    d.set_page_load_timeout(5)
    d.set_script_timeout(4)
    d.implicitly_wait(2)
    vw_adj = vw + random.randint(-5, 5)
    vh_adj = vh + random.randint(-5, 5)
    scale = random.choice([2.0, 2.5, 2.75, 3.0, 3.5])
    d.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "mobile": True, "width": vw_adj, "height": vh_adj,
        "deviceScaleFactor": scale, "screenOrientation": {"type": "portraitPrimary", "angle": 0},
        "touch": True,
    })
    # Block non-essential resources (fonts, media, trackers) for speed
    try:
        d.execute_cdp_cmd("Network.enable", {})
        d.execute_cdp_cmd("Network.setBlockedURLs", {"urls": [
            "*.woff", "*.woff2", "*.ttf", "*.eot",
            "*.mp4", "*.webm", "*.mp3", "*.ogg",
            "*facebook.com*", "*fbcdn*", "*analytics*", "*tracking*",
            "*gtag*", "*googletagmanager*", "*scorecardresearch*",
        ]})
    except: pass

    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": f"""
        Object.defineProperty(navigator,'webdriver',{{get:()=>undefined}});
        Object.defineProperty(navigator,'plugins',{{get:()=>[1,2,3,4,5]}});
        Object.defineProperty(navigator,'languages',{{get:()=>['en-US','en']}});
        Object.defineProperty(navigator,'hardwareConcurrency',{{get:()=>{hw_cores}}});
        Object.defineProperty(navigator,'deviceMemory',{{get:()=>{dev_mem}}});
        Object.defineProperty(navigator,'platform',{{get:()=>'Linux armv81'}});
        window.chrome = {{runtime:{{}}}};
        var origTR = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(){{
            var c = origTR.apply(this,arguments);
            if(c.length>100){{
                var i = {random.randint(0,99)};
                c = c.substring(0,i) + '{random.choice(["x","y","z","w","q"])}' + c.substring(i+1);
            }}
            return c;
        }};
        var origGL = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(){{
            var ctx = origGL.apply(this,arguments);
            if(ctx && ctx.getParameter){{
                var _gp = ctx.getParameter.bind(ctx);
                ctx.getParameter = function(p){{
                    if(p===37445) return '{webgl_vendor}';
                    if(p===37446) return '{webgl_renderer}';
                    return _gp(p);
                }};
            }}
            return ctx;
        }};
        var _getTz = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function(){{ return {tz}; }};
    """})
    return d

def cleanup_profile(p):
    """Remove the temp Chrome profile directory for this driver."""
    try:
        profile = p.capabilities.get("chrome", {}).get("userDataDir", "")
        if profile and profile.startswith("/tmp/ppccli_"):
            try: p.quit()
            except: pass
            time.sleep(0.5)
            subprocess.run(f"rm -rf '{profile}' 2>/dev/null", shell=True)
    except: pass

def cleanup_session():
    """Kill zombie Chrome processes and clean temp profiles.
    Called at the START of every session before workers launch.
    """
    try:
        for old_dir in glob.glob("/tmp/ppccli_*"):
            if os.path.isdir(old_dir):
                subprocess.run(f"pkill -9 -f '{old_dir}' 2>/dev/null", shell=True)
                subprocess.run(f"rm -rf '{old_dir}' 2>/dev/null", shell=True)
        subprocess.run("pkill -9 -f 'chrome.*--user-data-dir=/tmp/ppccli_' 2>/dev/null", shell=True)
        subprocess.run("pkill -9 -f chromedriver 2>/dev/null", shell=True)
    except: pass
    time.sleep(1)

def safe_navigate(p, url, retries=3):
    for attempt in range(retries):
        try:
            p.get(url)
            time.sleep(1.5)
            cu = safe_url(p)
            if "chrome-error" not in cu and "chromewebdata" not in cu:
                return True
            print(f"  [Nav] Chrome error attempt {attempt+1}, retrying...", flush=True)
        except Exception as e:
            print(f"  [Nav] Exception attempt {attempt+1}: {e}", flush=True)
            time.sleep(2)
    return False

# ──────────────────────────────────────────────
# PAGE HELPERS
# ──────────────────────────────────────────────
def dismiss_dialogs(p):
    try:
        try: alert = p.switch_to.alert; alert.dismiss(); time.sleep(0.5)
        except: pass
        p.execute_script("window.alert=function(){};window.confirm=function(){return true;};window.prompt=function(){return'';}")
    except: pass

def safe_url(p):
    try: return p.execute_script("return window.location.href") or ""
    except: return ""

def nuke_overlays(p):
    dismiss_dialogs(p)
    try:
        p.execute_script(NUKE_JS); time.sleep(0.1)
        p.execute_script("""
            document.querySelectorAll('[class*="close"],[aria-label*="Close"],[id*="close"],[class*="dismiss"],[aria-label*="Dismiss"]').forEach(function(e){
                if(e.offsetWidth>0&&e.offsetHeight>0){try{e.click()}catch(e){}}});
            document.querySelectorAll('*').forEach(function(e){
                if(e.offsetWidth>0&&e.offsetHeight>0&&(e.innerText=='\u00d7'||e.innerText=='\u2715')){try{e.click()}catch(e){}}});
        """)
        time.sleep(0.1)
    except: pass

def switch_main(p):
    if MAIN_HANDLE:
        try: p.switch_to.window(MAIN_HANDLE)
        except: pass

def close_extra_tabs(p):
    try:
        curr = p.current_window_handle
        for wh in p.window_handles:
            if wh != MAIN_HANDLE and wh != curr:
                try:
                    p.switch_to.window(wh)
                    cu = safe_url(p) or ""
                    # Keep about:blank tabs (still loading interstitial) and non-excluded destinations
                    if "about:blank" not in cu:
                        cd = urlparse(cu).netloc
                        if cd and not any(x in cd for x in EX_DOMAINS + SOCIAL_DOMAINS):
                            continue
                        p.close()
                except: pass
        p.switch_to.window(curr)
    except: pass

def reset_driver(p):
    try:
        for wh in p.window_handles:
            try: p.switch_to.window(wh); p.execute_script("localStorage.clear(); sessionStorage.clear();")
            except: pass
        while len(p.window_handles) > 1:
            p.switch_to.window(p.window_handles[-1]); p.close()
        p.switch_to.window(p.window_handles[0])
        p.execute_cdp_cmd("Network.clearBrowserCookies", {})
        p.execute_cdp_cmd("Network.clearBrowserCache", {})
        p.execute_script("window.location.href='about:blank'")
        time.sleep(0.5)
        return True
    except:
        return False

def scroll_incremental(p, steps=8):
    for i in range(steps):
        try: p.execute_script(f"window.scrollBy(0, document.body.scrollHeight/{steps});")
        except: break
        time.sleep(0.1)
    try: p.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    except: pass
    time.sleep(0.3)

def check_tab_dest(p, ex_domains):
    try:
        cu = safe_url(p)
        if cu:
            cd = urlparse(cu).netloc
            if cd and not any(x in cd for x in ex_domains + SOCIAL_DOMAINS):
                body = (p.execute_script("return (document.body.innerText||'').trim().length") or 0)
                if body > 50:
                    return True, cu
    except: pass
    return False, None

# ──────────────────────────────────────────────
# CLICK HELPERS
# ──────────────────────────────────────────────
def click_any(p, txt, bottom_up=False):
    try:
        sq = txt.replace("'", "\\'")
        ok = p.execute_script(f"""
            var terms = ['{sq}'];
            var lower_terms = terms.map(function(t){{return t.toLowerCase();}});
            var sel = 'button, a, input, span, div[role="button"], [class*="button"], [class*="btn"], [id*="continue"], [class*="continue"]';
            var els = document.querySelectorAll(sel);
            var start = {'els.length-1' if bottom_up else '0'};
            var end = {'-1' if bottom_up else 'els.length'};
            var step = {'-1' if bottom_up else '1'};
            for(var i=start;i{'!=' if bottom_up else '<'}end;i+=step){{var e=els[i];if(e.offsetWidth>0&&e.offsetHeight>0){{var t=(e.innerText||e.value||'').toLowerCase();for(var j=0;j<lower_terms.length;j++){{if(t.indexOf(lower_terms[j])!=-1){{e.scrollIntoView({{block:'center',behavior:'instant'}});e.click();setTimeout(function(){{e.click();}},100);setTimeout(function(){{e.click();}},200);return true;}}}}}}}}
            var all = document.querySelectorAll('*');
            for(var i=start;i{'!=' if bottom_up else '<'}end;i+=step){{var e=all[i];if(e.offsetWidth>0&&e.offsetHeight>0){{var t=(e.innerText||'').toLowerCase();if(t.indexOf(lower_terms[0])!=-1&&(e.tagName=='BUTTON'||e.tagName=='A'||e.tagName=='INPUT'||e.getAttribute('role')=='button')){{e.scrollIntoView({{block:'center',behavior:'instant'}});e.click();setTimeout(function(){{e.click();}},100);setTimeout(function(){{e.click();}},200);return true;}}}}}}
            return false;
        """)
        if ok:
            return True
        # Fallback: try known PPC template element IDs
        return click_by_id(p, ALL_TP_IDS)
    except: return False

def click_any_native(p, txt):
    try:
        terms = [txt.lower(), txt.upper(), txt]
        sel = "button, a, input, span, [role='button'], [class*='button'], [class*='btn']"
        for el in p.find_elements(By.CSS_SELECTOR, sel):
            if not el.is_displayed(): continue
            et = (el.text or "").lower()
            for term in terms:
                if et and term.lower() in et:
                    try: p.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el)
                    except: pass
                    el.click()
                    return True
        # Fallback: try known PPC template element IDs
        return click_by_id(p, ALL_TP_IDS)
    except:
        return False

def click_any_image(p):
    try:
        # Wait for images to load (up to 5s), then pick the best one
        for _ in range(10):
            ok = p.execute_script("""
                var best = null;
                var imgs = document.querySelectorAll('img');
                for(var i=0;i<imgs.length;i++){
                    var img=imgs[i];
                    var w = img.naturalWidth || img.offsetWidth;
                    var h = img.naturalHeight || img.offsetHeight;
                    if(w<35||h<35) continue;
                    var src=(img.src||'').toLowerCase();
                    if(src.indexOf('logo')!=-1) continue;
                    var parent=img.closest('a');
                    var href=(parent?parent.href:'').toLowerCase();
                    if(href.indexOf('hittracks')!=-1||href.indexOf('chrome-error')!=-1) continue;
                    if(href.indexOf('vplink')!=-1||href.indexOf('arolinks')!=-1||
                       href.indexOf('linkpays')!=-1||href.indexOf('savepe')!=-1){
                        best = {img:img, parent:parent, href:href}; break;
                    }
                    if(!best) best = {img:img, parent:parent, href:href};
                }
                if(best){
                    best.img.scrollIntoView({block:'center',behavior:'instant'});
                    if(best.parent) best.parent.click(); else best.img.click();
                    return true;
                }
                return false;
            """)
            if ok:
                return True
            time.sleep(0.5)
        return False
    except: return False

# PPC template element IDs (from linkpays-bypass template)
TP_IDS = {
    "go": ["goBtn"],
    "unlock": ["tp-unlock-btn"],
    "verify": ["tp-verify"],
    "continue": ["tp-snp2"],
    "wait": ["tp-wait1"],
}
ALL_TP_IDS = list({eid for ids in TP_IDS.values() for eid in ids})

def click_by_id(p, ids):
    try:
        for eid in ids:
            ok = p.execute_script(f"""
                var el = document.getElementById('{eid}');
                if(el && el.offsetWidth>0 && el.offsetHeight>0){{
                    el.scrollIntoView({{block:'center',behavior:'instant'}});
                    el.click();
                    return true;
                }}
                return false;
            """)
            if ok:
                return True
    except: pass
    return False

def delay(b=0.5, e=1.5):
    time.sleep(b + random.random() * (e - b))

def click_skip(p):
    for t in ["Skip","skip","SKIP","Dismiss","dismiss","Not granted","not granted","No thanks","Close"]:
        try:
            sq = t.replace("'", "\\'")
            r = p.execute_script(f"""
                var terms = ['{sq}'];
                var all = document.querySelectorAll('button, a, input, [role="button"], [class*="skip"], [class*="dismiss"], [aria-label*="Skip"]');
                for(var i=0;i<all.length;i++){{var e=all[i];if(e.offsetWidth>0&&e.offsetHeight>0){{var txt=(e.innerText||e.value||e.getAttribute('aria-label')||'').toLowerCase();for(var j=0;j<terms.length;j++){{if(txt.indexOf(terms[j].toLowerCase())!=-1){{e.scrollIntoView({{block:'center'}});e.click();return '{sq}';}}}}}}}}
                return '';
            """)
            if r: time.sleep(1); return True
        except: pass
    # Fallback: dismiss via known overlay close IDs
    try: return click_by_id(p, ["tp-overlay-close", "tp-close", "closeBtn", "overlay-close"])
    except: return False

def find_dest_in_page(p, ex_domains, force=False):
    try:
        txt = (p.execute_script("return document.body.innerText||''") or "").lower()
        if not force and any(ind in txt for ind in PPC_INDICATORS):
            return False, None
        links = p.execute_script("""
            var results = [];
            var els = document.querySelectorAll('a[href]');
            for(var i=0;i<els.length;i++){
                var href = els[i].href || '';
                if(href && href.indexOf('javascript')!==0){
                    results.push({href: href, text: (els[i].innerText||'').trim(), visible: els[i].offsetWidth>0&&els[i].offsetHeight>0});
                }
            }
            return results;
        """) or []
        for link in links:
            href = link.get("href", "")
            cd = urlparse(href).netloc
            if cd and not any(x in cd for x in ex_domains + SOCIAL_DOMAINS):
                safe_href = href.replace("'", "\\'")
                p.execute_script(f"window.location.href='{safe_href}'")
                time.sleep(3)
                return True, href
    except: pass
    return False, None

# ──────────────────────────────────────────────
# PPC ACTION PARSER
# ──────────────────────────────────────────────
def parse_ppc_actions(txt):
    t = txt.lower()
    actions = []
    if "not interested" in t or "not grant" in t:
        actions.append("not_interested")
    if "step 2/3" in t or "step 2 of 3" in t:
        actions.append("step2")
    if "please wait" in t or "skip timer" in t or \
       re.search(r'wait\s*\d*\s*(sec|second)', t, re.I) or \
       re.search(r'\d+\s*(sec|second)\s*(link|generating|remaining)', t, re.I) or \
       re.search(r'(?:linkpays\s+)?\d+\s*(sec|second)', t[:200], re.I) or \
       "loading the best option" in t:
        actions.append("timer")  # timer FIRST — prevents unlock from interrupting
    if "click any image" in t:
        actions.append("click_image")
    if "scroll down" in t and "continue" in t:
        actions.append("scroll_continue")
    if "verify" in t and any(x in t for x in [" click", " button", " now", " to ", "your", "destination"]):
        actions.append("verify")
    if "click below" in t or "click ads" in t:
        actions.append("click_ads")
    if "i'm not robot" in t or "unlock" in t or "not robot" in t:
        actions.append("unlock")
    if "telegram" in t:
        actions.append("telegram")
    if "get link" in t or "download" in t or "your link is almost ready" in t or "gate link" in t:
        actions.append("get_link")
    if not actions:
        actions = []  # no generic continue — let hop loop fallback to find_dest_in_page
    actions = list(OrderedDict.fromkeys(actions))
    return actions

def exec_ppc_action(p, a, ex_domains):
    global MAIN_HANDLE
    if a == "not_interested":
        for t in ["Continue","continue","CONTINUE","OK","Okay"]:
            if click_any(p, t): break
        time.sleep(1)
        close_extra_tabs(p)
        return False, None

    if a == "step2":
        txt = (p.execute_script("return document.body.innerText||''") or "").lower()
        if "click any image" in txt:
            for _ in range(14):
                time.sleep(1)
                try:
                    body = (p.execute_script("return document.body.innerText||''") or "").lower()
                    if "verify" in body and ("click to verify" in body or " button" in body or " continue" in body):
                        break
                except: pass
        for t in ["Verify","verify","VERIFY","click to verify"]:
            if click_any(p, t): time.sleep(1); break
        return False, None

    if a == "scroll_continue":
        scroll_incremental(p, 10)
        cu = safe_url(p); cd = urlparse(cu).netloc
        # Try domain-chain navigation: find a link to the next PPC domain
        for pcd, nxt in PPC_CHAIN.items():
            if pcd in cd:
                try:
                    links = p.execute_script("""
                        var results = []; var els = document.querySelectorAll('a[href]');
                        for(var i=0;i<els.length;i++){var e=els[i];if(e.offsetWidth>0&&e.offsetHeight>0&&e.href.indexOf('javascript')!==0){results.push(e.href);}}
                        return results;
                    """) or []
                    for href in links:
                        hn = urlparse(href).netloc
                        if any(x in hn for x in nxt):
                            safe_navigate(p, href)
                            return False, None
                except: pass
                break
        # Fallback: click Continue repeatedly (priority: button > a) until domain changes
        for _ in range(5):
            try:
                clicked = p.execute_script("""
                    // Priority 1: visible buttons with CONTINUE text
                    var els = document.querySelectorAll('button, input[type="submit"], [role="button"], [class*="btn"]');
                    for(var i=els.length-1;i>=0;i--){var e=els[i];if(e.offsetWidth>0&&e.offsetHeight>0){var t=(e.innerText||e.value||'').toUpperCase();if(t.indexOf('CONTINUE')!=-1){e.scrollIntoView({block:'center',behavior:'instant'});e.click();return true;}}}
                    // Priority 2: <a> links with CONTINUE text
                    var al = document.querySelectorAll('a');
                    for(var i=al.length-1;i>=0;i--){var e=al[i];if(e.offsetWidth>0&&e.offsetHeight>0){var t=(e.innerText||'').toUpperCase();if(t.indexOf('CONTINUE')!=-1){e.scrollIntoView({block:'center',behavior:'instant'});e.click();return true;}}}
                    // Priority 3: any element with class/id containing continue
                    var cx = document.querySelectorAll('[class*="continue"],[id*="continue"]');
                    for(var i=cx.length-1;i>=0;i--){var e=cx[i];if(e.offsetWidth>0&&e.offsetHeight>0&&e.tagName!='HTML'&&e.tagName!='BODY'){e.scrollIntoView({block:'center',behavior:'instant'});e.click();return true;}}
                    return false;
                """)
            except:
                clicked = False
            if not clicked:
                break
            time.sleep(1.5)
            cu2 = safe_url(p); cd2 = urlparse(cu2).netloc
            if cd2 != cd:
                break
        # Final fallback: if JS click loop didn't change domain, extract Continue href and navigate directly
        if safe_url(p) == cu:
            for _ in range(2):
                try:
                    href = p.execute_script("""
                        var els = document.querySelectorAll('a[href]');
                        for(var i=0;i<els.length;i++){
                            var e=els[i];
                            if(e.offsetWidth>0&&e.offsetHeight>0){
                                var t=(e.innerText||'').toUpperCase();
                                if(t.indexOf('CONTINUE')!=-1 && e.href && e.href.indexOf('javascript')!==0){
                                    e.scrollIntoView({block:'center',behavior:'instant'});
                                    return e.href;
                                }
                            }
                        }
                        return '';
                    """) or ""
                    if href:
                        safe_navigate(p, href)
                        cu2 = safe_url(p); cd2 = urlparse(cu2).netloc
                        if cd2 != cd:
                            break
                except: pass
        return False, None

    if a == "click_image":
        click_any_image(p); time.sleep(1)
        return False, None

    if a == "verify":
        scroll_incremental(p, 5)
        for t in ["Verify","verify","VERIFY","click to verify"]:
            if click_any(p, t): time.sleep(0.5); break
        scroll_incremental(p, 3)
        for t in ["Continue","continue","CONTINUE"]:
            if click_any(p, t):
                time.sleep(1)
                break
        return False, None

    if a == "click_ads":
        click_any_image(p); time.sleep(1)
        # After clicking, check if Get Link appeared and auto-click it
        body = (p.execute_script("return document.body.innerText||''") or "").lower()
        if "get link" in body or "download" in body or "your link" in body:
            for t in ["Get Link","get link","Download","download","GET LINK","DOWNLOAD","Gate Link"]:
                if click_any(p, t):
                    time.sleep(2)
                    break
        return False, None

    if a == "get_link":
        scroll_incremental(p, 6)
        time.sleep(1)
        n_wh = len(p.window_handles)
        for t in ["Get Link","get link","Download","download","GET LINK","DOWNLOAD","Destination Link","Click Here","Gate Link"]:
            if click_any_native(p, t) or click_any(p, t, bottom_up=True):
                break
        time.sleep(2)
        if len(p.window_handles) > n_wh:
            try:
                p.switch_to.window(p.window_handles[-1])
                for _ in range(20):
                    time.sleep(0.5)
                    cu_pop = safe_url(p)
                    if cu_pop and "about:blank" not in cu_pop:
                        cd_pop = urlparse(cu_pop).netloc
                        if cd_pop:
                            if not any(x in cd_pop for x in ex_domains):
                                return True, cu_pop
                            # PPC-domain in new tab — adopt it as current tab
                            MAIN_HANDLE = p.current_window_handle
                        break
            except: pass
        cu_post = safe_url(p)
        cd_post = urlparse(cu_post).netloc
        if cd_post and not any(x in cd_post for x in ex_domains):
            return True, cu_post
        # If no new tab opened and click didn't work, wait and retry (button may not be ready)
        for retry in range(3):
            n_wh2 = len(p.window_handles)
            for t in ["Get Link","get link","Download","download","GET LINK","DOWNLOAD","Destination Link","Click Here","Gate Link"]:
                if click_any_native(p, t) or click_any(p, t, bottom_up=True):
                    break
            time.sleep(2)
            if len(p.window_handles) > n_wh2:
                try:
                    p.switch_to.window(p.window_handles[-1])
                    for _ in range(20):
                        time.sleep(0.5)
                        cu_pop = safe_url(p)
                        if cu_pop and "about:blank" not in cu_pop:
                            cd_pop = urlparse(cu_pop).netloc
                            if cd_pop:
                                if not any(x in cd_pop for x in ex_domains):
                                    return True, cu_pop
                                MAIN_HANDLE = p.current_window_handle
                            break
                except: pass
            # Check if current page navigated to destination
            cu_retry = safe_url(p)
            cd_retry = urlparse(cu_retry).netloc
            if cd_retry and not any(x in cd_retry for x in ex_domains):
                return True, cu_retry
            if n_wh2 == len(p.window_handles):
                time.sleep(3)
        return False, None

    if a == "telegram":
        n_wh = len(p.window_handles)
        for t in ["Telegram","telegram","Join Our"]:
            if click_any(p, t): time.sleep(3); break
        if len(p.window_handles) > n_wh:
            try:
                p.switch_to.window(p.window_handles[-1])
                time.sleep(3)
            except: pass
        return False, None

    if a == "unlock":
        for t in ["I'M Not Robot","Not Robot","Unlock","IM","I'M"]:
            if click_any(p, t): time.sleep(2); break
        return False, None

    if a == "timer":
        txt = (p.execute_script("return document.body.innerText||''") or "").lower()
        # Try to skip timer if page offers a skip mechanism
        if "skip timer" in txt or "click any image" in txt or "click ads" in txt or "click below" in txt:
            click_any_image(p); time.sleep(0.3)
            body = (p.execute_script("return document.body.innerText||''") or "").lower()
            if "get link" in body or "download" in body or "your link" in body or "destination" in body:
                return False, None
        m = re.search(r'wait\s*(\d+)\s*(sec|second)', txt, re.I)
        if not m:
            m = re.search(r'(\d+)\s*(sec|second)\s*(link|generating|remaining)', txt, re.I)
        if not m:
            m = re.search(r'(?:linkpays\s+)?(\d+)\s*(sec|second)', txt[:200], re.I)
        sec = int(m.group(1)) if m else 16
        # Only break early if text appears NEW (wasn't present when timer started)
        initial_text = txt
        for i in range(sec):
            time.sleep(1)
            try:
                body = (p.execute_script("return document.body.innerText||''") or "").lower()
                # "get link" or "download" appearing = timer finished
                if ("get link" in body and "get link" not in initial_text) or \
                   ("download" in body and "download" not in initial_text):
                    break
            except: pass
        # Small grace period for JS to enable the button after the countdown
        time.sleep(2)
        return False, None

    return False, None

# ──────────────────────────────────────────────
# GOOG_REWARDED HANDLER
# ──────────────────────────────────────────────
def handle_goog_rewarded(p):
    nuke_overlays(p); click_skip(p); time.sleep(0.5)
    nuke_overlays(p); click_skip(p); time.sleep(0.5)
    # Wait for interstitial ad to complete (up to 15s)
    for s in range(20):
        time.sleep(0.5)
        cu = safe_url(p)
        # Check if interstitial is gone (no goog_vignette/goog_rewarded in URL)
        if "#google_vignette" not in cu and "#goog_rewarded" not in cu:
            break
        # Try to find and dismiss Continue/Skip/Close buttons inside the interstitial
        try:
            dismissed = p.execute_script("""
                function tryClick(doc){
                    var sel = doc.querySelectorAll('button, a, [class*="continue"], [id*="continue"], [class*="skip"], [class*="dismiss"], [class*="close"]');
                    for(var i=0;i<sel.length;i++){var e=sel[i];if(e.offsetWidth>0&&e.offsetHeight>0){var t=(e.innerText||e.value||'').toUpperCase();if(t.indexOf('CONTINUE')!=-1||t.indexOf('SKIP')!=-1||t.indexOf('DISMISS')!=-1||t.indexOf('CLOSE')!=-1||t.indexOf('NOT INTERESTED')!=-1||t.indexOf('NO THANKS')!=-1){e.scrollIntoView({block:'center',behavior:'instant'});e.click();return true;}}}
                    return false;
                }
                if(tryClick(document))return true;
                var ifs = document.querySelectorAll('iframe');
                for(var i=0;i<ifs.length;i++){try{if(ifs[i].contentDocument&&tryClick(ifs[i].contentDocument))return true;}catch(e){}}
                return false;
            """)
        except:
            dismissed = False
        if dismissed:
            break
        # Check for new tabs (destination may open in background)
        n_wh = len(p.window_handles)
        if n_wh > 1:
            try:
                p.switch_to.window(p.window_handles[-1])
                pop_url = safe_url(p)
                if pop_url and "about:blank" not in pop_url:
                    pop_cd = urlparse(pop_url).netloc
                    if pop_cd and not any(x in pop_cd for x in EX_DOMAINS):
                        return  # destination detected in new tab
                p.switch_to.window(p.window_handles[0])
            except: pass
    # Hard fallback: strip fragment and reload to escape google_vignette
    switch_main(p)
    cu = safe_url(p)
    if "#google_vignette" in cu or "#goog_rewarded" in cu:
        clean = cu.split("#")[0] if "#" in cu else cu
        if clean:
            safe_navigate(p, clean)

# ──────────────────────────────────────────────
# IP ROTATION
# ──────────────────────────────────────────────
def check_ip():
    try:
        resp = urllib.request.urlopen("https://ipinfo.io/ip", timeout=8)
        ip = resp.read().decode().strip()
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip): return ip
    except: pass
    return None

def rotate_ip():
    macrodroid = ["http://127.0.0.1:8080/rotate_ip", "http://100.91.72.157:8080/rotate_ip"]
    def _md():
        for u in macrodroid:
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, method="GET"), timeout=5)
                if r.status == 200: return True
            except: pass
        return False
    def _check_network(timeout=30):
        for _ in range(0, timeout, 2):
            time.sleep(2)
            try:
                urllib.request.urlopen("https://ipinfo.io/ip", timeout=5)
                return True
            except: pass
        return False
    # Clean any stale lock before attempting
    try:
        st = os.stat(ROTATE_LOCK)
        if time.time() - st.st_mtime > 30:
            os.rmdir(ROTATE_LOCK)
    except (FileNotFoundError, OSError): pass

    try:
        os.mkdir(ROTATE_LOCK)
        primary = True
    except FileExistsError:
        primary = False
    if not primary:
        print("  [IP] Waiting for another process to finish rotation...", flush=True)
        for _ in range(20):
            time.sleep(2)
            try:
                urllib.request.urlopen("https://ipinfo.io/ip", timeout=5)
                print("  [IP] Network OK (secondary)", flush=True)
                new_ip = check_ip() or "unknown"
                print(f"  [IP] New: {new_ip}", flush=True)
                return True
            except: pass
        print("  [IP] Secondary wait timed out", flush=True)
        return False
    old_ip = check_ip() or "unknown"
    print(f"  [IP] Current: {old_ip}", flush=True)
    if not _md():
        print("  [IP] MacroDroid unreachable", flush=True)
        try: os.rmdir(ROTATE_LOCK)
        except: pass
        return False

    # Keep toggling until IP actually changes (up to 10 attempts)
    for attempt in range(1, 11):
        print(f"  [IP] Toggle {attempt}/10", flush=True)
        _md()
        time.sleep(8)
        if _check_network(timeout=25):
            new_ip = check_ip()
            if new_ip and new_ip != old_ip:
                print(f"  [IP] IP changed: {old_ip} → {new_ip}", flush=True)
                break
            print(f"  [IP] IP unchanged ({new_ip}) — toggling again...", flush=True)
        else:
            print("  [IP] Network down — toggling again...", flush=True)
    else:
        print("  [IP] Failed to change IP after 10 attempts", flush=True)

    new_ip = check_ip() or "unknown"
    changed = new_ip != old_ip and old_ip != "unknown" and new_ip != "unknown"
    print(f"  [IP] New: {new_ip} | Changed: {'YES' if changed else 'NO'}", flush=True)
    try: os.rmdir(ROTATE_LOCK)
    except: pass
    return changed

# ──────────────────────────────────────────────
# CORE FLOW
# ──────────────────────────────────────────────
def run_view(p, url):
    global MAIN_HANDLE
    MAIN_HANDLE = None
    p.execute_cdp_cmd("Network.clearBrowserCookies", {})
    p.execute_cdp_cmd("Network.clearBrowserCache", {})
    try: p.execute_script("localStorage.clear(); sessionStorage.clear();")
    except: pass
    ref = os.environ.get("REFERRER_URL", "")
    if ref:
        p.execute_cdp_cmd("Page.navigate", {"url": url, "referrer": ref})
        time.sleep(1)
    else:
        p.get(url)
    time.sleep(2)
    MAIN_HANDLE = p.current_window_handle
    # Inject view-counter request tracker (injects into all frames)
    p.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
        window.__ppcView = null;
        var _origOpen = XMLHttpRequest.prototype.open;
        if(_origOpen){ XMLHttpRequest.prototype.open = function(method, url){
            if(method&&method.toLowerCase()==='post'&&url&&url.indexOf('linkpays')!==-1){
                window.__ppcView = url;
                console.log('[ppc] View counter:', url);
            }
            return _origOpen.apply(this,arguments);
        };}
    """})

    ex_domains = EX_DOMAINS[:]
    same_url_count = 0
    last_url = None
    last_text = None
    same_text_count = 0
    err_count = 0
    stuck_count = 0
    for hop in range(45):
        time.sleep(0.2)
        switch_main(p)
        dismiss_dialogs(p)
        nuke_overlays(p)

        for wh in p.window_handles:
            try:
                p.switch_to.window(wh); time.sleep(0.15)
                f, d = check_tab_dest(p, ex_domains)
                if f:
                    return True, d
            except: pass
        switch_main(p)

        cu = safe_url(p)
        cd = urlparse(cu).netloc
        print(f"  Hop {hop+1}: {cu[:80]}", flush=True)

        # Google CAPTCHA / sorry page — fast fail
        if "google.com/sorry" in cu or "/sorry/index" in cu:
            print("  [Abort] Google CAPTCHA block — skipping", flush=True)
            return False, None

        # Chrome-error abort
        if "chrome-error" in cu or "chromewebdata" in cd:
            err_count += 1
            if err_count >= 3:
                print("  [Abort] Chrome error 3x — skipping", flush=True)
                return False, None
        else:
            err_count = max(0, err_count - 1)

        # Skip excluded domains (no action parsing)
        if cd and not any(x in cd for x in ex_domains + SOCIAL_DOMAINS):
            try:
                txt_check = (p.execute_script("return document.body.innerText||''") or "").lower()
                if any(ind in txt_check for ind in PPC_INDICATORS):
                    ex_domains.append(cd)
                    continue
            except: pass
            print(f"  Destination: {cu[:100]}", flush=True)
            return True, cu

        # Same URL tracking
        if cu == last_url:
            same_url_count += 1
        else:
            same_url_count = 0
        last_url = cu

        # Content-based stuck detection — only abort if page has NO remaining PPC indicators
        cur_text = (p.execute_script("return (document.body.innerText||'').substring(0,300)") or "").strip()
        if cur_text and cur_text == last_text:
            same_text_count += 1
            has_indicators = any(ind in cur_text.lower() for ind in PPC_INDICATORS)
            if same_text_count >= 5 and not has_indicators:
                print(f"  [Abort] Same page content {same_text_count}x with no indicators — skipping", flush=True)
                return False, None
        else:
            same_text_count = 0
        last_text = cur_text

        # Stuck handler
        if same_url_count >= 8:
            stuck_count += 1
            if stuck_count >= 3:
                print("  [Abort] Page stuck 3x — skipping", flush=True)
                return False, None
            nuke_overlays(p)
            scroll_incremental(p, 15)
            for t in ["Get Link","get link","Download","download","Get Destination Link","Destination Link"]:
                if click_any(p, t): time.sleep(2); break
            cd_stuck = urlparse(cu).netloc
            if cd_stuck and not any(x in cd_stuck for x in ex_domains):
                found, dest = find_dest_in_page(p, ex_domains, force=True)
                if found:
                    return True, dest

        nuke_overlays(p)

        # Initial goBtn click on linkpays.in (first hop)
        if hop == 0 and click_by_id(p, ["goBtn"]):
            print("  [goBtn] Clicked — registering view...", flush=True)
            time.sleep(3)
            # Check if view counter request was tracked
            view_hit = p.execute_script("return window.__ppcView || null;") or ""
            if view_hit:
                print(f"  [View] Counter confirmed: {view_hit[:60]}", flush=True)
            else:
                print("  [View] No explicit counter request detected (view may still count)", flush=True)

        # Skip action parsing on dead-end pages — go straight to destination scan
        cu_path = urlparse(cu).path.lower()
        if any(x in cu_path for x in ["privacy", "disclaimer", "terms", "policy", "copyright"]):
            found, dest = find_dest_in_page(p, ex_domains, force=True)
            if found:
                return True, dest
            print("  [Skip] Privacy/policy page — scanning for destination...", flush=True)
            continue

        # Gateway handler
        if hop < 3:
            gw_found = False
            for t in ["Continue to Next", "continue to next", "CONTINUE TO NEXT", "Continue", "continue", "CONTINUE"]:
                if click_any(p, t):
                    time.sleep(2)
                    gw_found = True
                    break
            if gw_found:
                switch_main(p); time.sleep(0.5)
                continue

        # Google interstitial
        cu_frag = urlparse(cu).fragment
        if "#goog_rewarded" in cu or "#google_vignette" in cu or cu_frag == "go" or cu_frag.startswith("go/"):
            cu_before = safe_url(p).split("#")[0]
            handle_goog_rewarded(p)
            switch_main(p)
            cu = safe_url(p); cd = urlparse(cu).netloc
            if cd and not any(x in cd for x in ex_domains):
                return True, cu
            # If still on same base URL after vignette, try Continue once more
            if cu.split("#")[0] == cu_before:
                for _ in range(2):
                    for t in ["Continue", "continue", "CONTINUE", "Click Here", "Proceed", "Gate Link", "Get Link"]:
                        if click_any(p, t):
                            time.sleep(2)
                            break
                    cu2 = safe_url(p)
                    if cu2.split("#")[0] != cu_before:
                        break
                    time.sleep(2)
                cu = safe_url(p); cd = urlparse(cu).netloc
                if cd and not any(x in cd for x in ex_domains):
                    return True, cu
            continue

        # Ad pages
        if any(x in cd for x in ["msc", "doubleclick", "google"]):
            for t in ["Accept All","Continue","I Agree","Got it","Allow","OK"]:
                if click_any(p, t): time.sleep(1)
            time.sleep(3)
            close_extra_tabs(p)
            continue

        # Read page and parse actions
        txt = ""
        for _ in range(5):
            try:
                txt = p.execute_script("return document.body.innerText||''") or ""
                if txt.strip(): break
            except: pass
            time.sleep(1)
        print(f"  Text: {txt[:120].replace(chr(10),' ')}", flush=True)
        actions = parse_ppc_actions(txt)
        # Supplement text-based detection with template element ID checks
        if "timer" not in actions and "unlock" not in actions:
            try:
                ids_found = p.execute_script("""
                    var ids = ['tp-unlock-btn','tp-verify','tp-snp2','goBtn','tp-wait1'];
                    for(var i=0;i<ids.length;i++){var el=document.getElementById(ids[i]);if(el&&el.offsetWidth>0&&el.offsetHeight>0)return ids[i];}
                    return '';
                """) or ""
                if ids_found == "tp-wait1" and "timer" not in actions:
                    actions.append("timer")
                if ids_found == "tp-unlock-btn" and "unlock" not in actions:
                    actions.append("unlock")
                if ids_found == "tp-verify" and "verify" not in actions:
                    actions.append("verify")
                if ids_found == "tp-snp2" and "scroll_continue" not in actions:
                    actions.append("scroll_continue")
                if ids_found == "goBtn" and "get_link" not in actions:
                    actions.append("get_link")
                actions = list(OrderedDict.fromkeys(actions))
            except: pass
        print(f"  Actions: {actions}", flush=True)
        url_changed = False

        for a in actions:
            prev_url = safe_url(p)
            dest_found, dest_url = exec_ppc_action(p, a, ex_domains)
            time.sleep(0.2)

            if dest_found:
                return True, dest_url

            # Check all tabs for destination
            for wh in p.window_handles:
                try:
                    p.switch_to.window(wh); time.sleep(0.15)
                    f, d = check_tab_dest(p, ex_domains)
                    if f:
                        return True, d
                except: pass
            switch_main(p)
            close_extra_tabs(p)

            cu2 = safe_url(p)
            cd2 = urlparse(cu2).netloc
            if cd2 and not any(x in cd2 for x in ex_domains):
                print(f"  Destination: {cu2[:80]}", flush=True)
                return True, cu2
            if cu2 and cu2 != prev_url:
                print(f"  URL changed: {cu2[:60]}", flush=True)
                # If still on same PPC domain after Continue, try more Continue clicks
                if cd2 and any(x in cd2 for x in PPC_DOMAINS) and a == "scroll_continue":
                    for t2 in ["Gate Link","Get Link","Click Here","Proceed","Download","Destination Link","Continue","continue","CONTINUE"]:
                        if click_any(p, t2):
                            time.sleep(2)
                            break
                    cu3 = safe_url(p)
                    cd3 = urlparse(cu3).netloc
                    if cd3 and not any(x in cd3 for x in ex_domains):
                        print(f"  Destination: {cu3[:80]}", flush=True)
                        return True, cu3
                break

        # If URL changed during actions, skip fallback DOM scan — let next hop process the new page
        url_changed = safe_url(p) != cu

        # Post-action Get Link check
        if "get_link" not in actions:
            gl_clicked = False
            for _ in range(2):
                time.sleep(1)
                for wh in p.window_handles:
                    try:
                        p.switch_to.window(wh)
                        f, d = check_tab_dest(p, ex_domains)
                        if f:
                            return True, d
                    except: pass
                switch_main(p)
                cu2 = safe_url(p)
                if cu2 != cu:
                    break
                if gl_clicked:
                    break
                for t in ["Get Link","get link","Download","download","Destination Link","Gate Link"]:
                    if click_any(p, t):
                        gl_clicked = True
                        time.sleep(3)
                        break

        # Fallback DOM scan — skip when URL changed (let next hop process the new page)
        if not url_changed:
            found, dest = find_dest_in_page(p, ex_domains)
            if found:
                return True, dest
            # PPC-domain article page with no indicators/actions — treat as final destination
            if cd and any(x in cd for x in PPC_DOMAINS) and not actions and txt.strip() and \
               not any(ind in txt.lower() for ind in PPC_INDICATORS):
                print(f"  Destination (PPC article): {cu[:80]}", flush=True)
                return True, cu

    # After hop loop exhausted
    switch_main(p); time.sleep(1)
    cu = safe_url(p)
    cd = urlparse(cu).netloc
    if cd and not any(x in cd for x in ex_domains):
        return True, cu
    return False, None

# ──────────────────────────────────────────────
# WORKER
# ──────────────────────────────────────────────
def worker(url, total_views):
    rotate = os.environ.get("ROTATE_IP", "").lower() not in ("0","off","false","no")
    p = make_driver()
    try:
        for v in range(total_views):
            print(f"\n{'='*50}\n  View {v+1}/{total_views}\n{'='*50}", flush=True)
            cleanup_session()
            ip_rotated = False
            if rotate:
                ip_rotated = rotate_ip()
                if not ip_rotated:
                    print("  [IP] Rotation FAILED — continuing with same IP", flush=True)
                time.sleep(1)
            ip = check_ip()
            print(f"  IP: {ip or 'unknown'}", flush=True)
            if not reset_driver(p):
                cleanup_profile(p)
                p = make_driver()
            ok, dest_url = run_view(p, url)
            if not ok:
                print(f"  [Retry] Restarting view {v+1}...", flush=True)
                if rotate and not ip_rotated:
                    if not rotate_ip():
                        print("  [IP] Rotation FAILED on retry", flush=True)
                    time.sleep(1)
                ip = check_ip()
                if not reset_driver(p):
                    cleanup_profile(p)
                    p = make_driver()
                ok, dest_url = run_view(p, url)
            if ok and dest_url:
                print(f"  {'[✓] SUCCESS'}  → {dest_url[:100]}", flush=True)
            else:
                print(f"  {'[✓] SUCCESS' if ok else '[✗] FAILED'}", flush=True)
    finally:
        cleanup_profile(p)

# ──────────────────────────────────────────────
# PARALLEL WORKER ORCHESTRATOR
# ──────────────────────────────────────────────
mp_ctx = multiprocessing.get_context("spawn")

def _worker_process(url, worker_id, result_queue):
    """Run one worker in its own process with dedicated display."""
    display_num = 99 + worker_id
    vnc_port = 5900 + worker_id
    os.environ["DISPLAY"] = f":{display_num}"
    os.environ["VNC_PORT"] = str(vnc_port)
    dest_url = None
    try:
        p = make_driver()
        try:
            ok, dest_url = run_view(p, url)
        finally:
            cleanup_profile(p)
    except Exception as e:
        print(f"  [Worker {worker_id}] Error: {e}", flush=True)
        ok = False
    result_queue.put((worker_id, url, ok, dest_url))

def orchestrate_parallel(urls, windows, same_ips, views, rotate, no_vnc, all_parallel=False):
    """Parallel orchestrator: sessions → rotate IP → start all workers → summary.
    
    Workers marked same_ip=True are launched together in one session on one IP.
    Workers marked same_ip=False each get their own session with IP rotation.
    When all_parallel=True, ALL workers go into ONE batch session regardless.
    """
    # Build worker groups: (same_ip, url, id) tuples
    wid = 0
    groups = []  # list of lists: each group = [worker, worker, ...]
    for ui, u in enumerate(urls):
        same = same_ips[ui] if ui < len(same_ips) else True
        batch = []
        for _ in range(windows[ui] if ui < len(windows) else 1):
            batch.append({"id": wid, "url": u, "label": f"URL{ui+1}.{wid+1}", "same_ip": same})
            wid += 1
        if same:
            groups.append(batch)
        else:
            for w in batch:
                groups.append([w])

    # all_parallel: merge ALL workers into one single batch session
    if all_parallel and len(groups) > 1:
        merged = []
        for g in groups:
            merged.extend(g)
        groups = [merged]

    all_workers = [w for g in groups for w in g]
    if not all_workers:
        print("  No workers defined.", flush=True)
        return False

    print(f"\n  Parallel workers: {len(all_workers)} in {len(groups)} group(s)", flush=True)
    for gi, g in enumerate(groups):
        same_label = "same IP" if len(g) > 1 and g[0]["same_ip"] else "separate session"
        for w in g:
            ip_info = f"Display :{99 + w['id']}" + (f"  VNC :{5900 + w['id']}" if not no_vnc else "")
            print(f"    Group {gi+1} [{w['label']}] {w['url'][:55]}  ({ip_info})", flush=True)

    session_count = 0
    overall_success = False
    for session in range(views):
        for gi, group in enumerate(groups):
            session_count += 1
            group_label = f"Group {gi+1}" if len(groups) > 1 else ""
            print(f"\n{'='*60}", flush=True)
            print(f"  Session {session_count}  {group_label}  |  {len(group)} worker(s)  |  "
                  f"{'with IP rotation' if rotate else 'no IP rotation'}", flush=True)
            print(f"{'='*60}", flush=True)

            cleanup_session()
            if rotate:
                print(f"\n  Rotating IP before session...", flush=True)
                ip_ok = rotate_ip()
                time.sleep(2)
                current_ip = check_ip()
                print(f"  Global IP: {current_ip or 'unknown'}", flush=True)

            session_start = time.time()
            rq = mp_ctx.Queue()
            procs = []
            for w in group:
                p = mp_ctx.Process(target=_worker_process, args=(w["url"], w["id"], rq))
                p.start()
                procs.append(p)
                print(f"  [Started] {w['label']} — Display :{99 + w['id']}", flush=True)

            for p in procs:
                p.join()

            results = []
            while not rq.empty():
                results.append(rq.get())

            elapsed = time.time() - session_start
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            if elapsed >= 3600:
                elapsed_str = f"{int(elapsed//3600):02d}:{int(elapsed%3600)//60:02d}:{int(elapsed%60):02d}"

            successes = sum(1 for r in results if r[2])
            total = len(results)
            rate = (successes * 100 // total) if total else 0

            print(f"\n  {'='*50}", flush=True)
            print(f"  Session {session_count} Summary", flush=True)
            print(f"  {'='*50}", flush=True)
            for r in sorted(results, key=lambda x: x[0]):
                wid, orig_url, ok, dest = r[0], r[1], r[2], r[3] if len(r) > 3 else None
                status = "[✓] SUCCESS" if ok else "[✗] FAILED"
                dest_str = f"  → {dest[:100]}" if ok and dest else ""
                print(f"    Worker {wid}: {status}{dest_str}", flush=True)
            print(f"  {'='*50}", flush=True)
            print(f"  Result: {successes}/{total} succeeded  ({rate}%)  |  Time: {elapsed_str}", flush=True)

            if successes > 0:
                overall_success = True

    if overall_success:
        print(f"\n  {'='*40}", flush=True)
        print(f"  ALL SESSIONS COMPLETE — success", flush=True)
        return True

    print(f"\n  All sessions exhausted — no successful views.", flush=True)
    return False

def interactive_parallel():
    """Interactive prompt for parallel mode."""
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║     ppccli — Parallel Mode           ║")
    print("  ║   Multi-window parallel orchestrator  ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    urls = []
    windows = []
    same_ips = []

    def add_url(net_name, net_example):
        url = ""
        while not url.strip():
            url = input(f"  {net_name} URL (e.g. {net_example}) [blank to skip]: ").strip()
            if not url:
                return None
        win_str = input(f"  Windows for this URL (default: 1): ").strip()
        try:
            win = int(win_str) if win_str else 1
        except ValueError:
            win = 1
        same_str = input(f"  Same IP for all windows? (Y/n): ").strip().lower()
        same = same_str not in ("n", "no")
        urls.append(url)
        windows.append(win)
        same_ips.append(same)
        return url

    print("  Enter URLs for each network (blank line to skip):")
    print()
    add_url("VPLINK/AroLinks", "https://arolinks.com/zREqi")
    add_url("LinkPays", "https://savepe.in/XXXXX")
    add_url("Custom", "https://example.com/ppc-link")

    while True:
        more = input("  Add another URL? (y/N): ").strip().lower()
        if more not in ("y", "yes"):
            break
        url = ""
        while not url.strip():
            url = input("  URL: ").strip()
        win_str = input(f"  Windows for this URL (default: 1): ").strip()
        try:
            win = int(win_str) if win_str else 1
        except ValueError:
            win = 1
        same_str = input(f"  Same IP for all windows? (Y/n): ").strip().lower()
        same = same_str not in ("n", "no")
        urls.append(url)
        windows.append(win)
        same_ips.append(same)

    if not urls:
        print("  No URLs provided. Exiting.", flush=True)
        sys.exit(0)

    print()
    views_str = input("  Total view sessions (default: 1): ").strip()
    try:
        views = int(views_str) if views_str else 1
    except ValueError:
        views = 1
    print()

    rotate_str = input("  Rotate IP between sessions? (y/N): ").strip().lower()
    if rotate_str in ("y", "yes"):
        os.environ.pop("ROTATE_IP", None)
        rotate = True
    else:
        os.environ["ROTATE_IP"] = "0"
        rotate = False
    print()

    vnc_str = input("  Start VNC servers? (y/N): ").strip().lower()
    if vnc_str in ("y", "yes"):
        os.environ.pop("NO_VNC", None)
        no_vnc = False
    else:
        os.environ["NO_VNC"] = "1"
        no_vnc = True
    print()

    allp_str = input("  Run ALL workers in one batch session (single IP)? (Y/n): ").strip().lower()
    all_parallel = allp_str not in ("n", "no")
    if all_parallel:
        print("    → All workers will run simultaneously in one session.")
    else:
        print("    → Workers grouped by URL and same-IP setting.")
    print()

    ref = input("  YouTube referrer URL (optional): ").strip()
    if ref:
        os.environ["REFERRER_URL"] = ref

    total_workers = sum(windows)
    print()
    print(f"  URLs:     {len(urls)}")
    for i, u in enumerate(urls):
        same_label = "same IP" if same_ips[i] else "separate IPs"
        print(f"    URL{i+1}: {u[:60]}  ({windows[i]} win, {same_label})")
    print(f"  Workers:  {total_workers}")
    print(f"  Sessions: {views}")
    print(f"  Rotate:   {'yes' if rotate else 'no'}")
    print(f"  VNC:      {'yes' if not no_vnc else 'no'}")
    print(f"  All batch: {'yes' if all_parallel else 'no'}")
    print(f"  Referrer: {ref or '(none)'}")
    print()

    confirm = input("  Start? (Y/n): ").strip().lower()
    if confirm in ("n", "no"):
        print("  Cancelled.")
        sys.exit(0)

    return urls, windows, same_ips, views, rotate, no_vnc, all_parallel

# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
def interactive_prompt():
    """Interactive CLI mode — asks questions step by step."""
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║           ppccli — Interactive        ║")
    print("  ║     Universal PPC Page Navigator      ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    mode = input("  Mode: (s)ingle or (p)arallel? [s]: ").strip().lower()
    if mode in ("p", "parallel"):
        urls, windows, same_ips, views, rotate, no_vnc, all_parallel = interactive_parallel()
        return urls, windows, same_ips, views, rotate, no_vnc, all_parallel, True

    print()
    print("  Network:")
    print("     1 → VPLINK / AroLinks (hittracks → krishitalk)")
    print("     2 → LinkPays (savepe.in / rank1st.in)")
    print("     3 → Custom (any other PPC URL)")
    net = input("  Your choice (1-3) [1]: ").strip() or "1"
    print()

    examples = {"1": "https://arolinks.com/zREqi", "2": "https://savepe.in/XXXXX", "3": "https://example.com/ppc-link"}
    labels = {"1": "VPLINK/AroLinks", "2": "LinkPays", "3": "Custom"}
    url = ""
    while not url.strip():
        url = input(f"  {labels.get(net, 'PPC')} URL (e.g. {examples.get(net, 'https://...')}): ").strip()
        if not url:
            print("  URL is required.")
    print()

    views_str = input("  Number of views (default: 1): ").strip()
    try:
        views = int(views_str) if views_str else 1
    except ValueError:
        print(f"  Invalid number, using 1.")
        views = 1
    print()

    rotate_str = input("  Rotate IP between views? (y/N): ").strip().lower()
    if rotate_str in ("y", "yes"):
        os.environ.pop("ROTATE_IP", None)
    else:
        os.environ["ROTATE_IP"] = "0"
    print()

    vnc_str = input("  Start VNC server? (y/N): ").strip().lower()
    if vnc_str in ("y", "yes"):
        os.environ.pop("NO_VNC", None)
    else:
        os.environ["NO_VNC"] = "1"
    print()

    ref = input("  YouTube referrer URL (optional): ").strip()
    if ref:
        os.environ["REFERRER_URL"] = ref

    print()
    print(f"  Network:  {labels.get(net, 'Custom')}")
    print(f"  URL:      {url}")
    print(f"  Views:    {views}")
    print(f"  Rotate:   {'yes' if rotate_str in ('y','yes') else 'no'}")
    print(f"  VNC:      {'yes' if vnc_str in ('y','yes') else 'no'}")
    print(f"  Referrer: {ref or '(none)'}")
    print()

    confirm = input("  Start? (Y/n): ").strip().lower()
    if confirm in ("n", "no"):
        print("  Cancelled.")
        sys.exit(0)

    return url, views, 1, True, True, False  # url, views, windows_per_url, rotate, no_vnc, is_parallel

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ppccli — Universal PPC page flow navigator")
    parser.add_argument("url", nargs="*", help="PPC URL(s) (e.g. https://vplink.in/MGIt8)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode (ask questions)")
    parser.add_argument("-p", "--parallel", action="store_true", help="Parallel mode (multi-window)")
    parser.add_argument("-n", "--views", type=int, default=1, help="Number of views/sessions (default: 1)")
    parser.add_argument("-w", "--windows", type=int, default=1, help="Windows per URL in parallel mode (default: 1)")
    parser.add_argument("--no-rotate", action="store_true", help="Skip IP rotation")
    parser.add_argument("--same-ip", action="store_true", default=True, dest="same_ip", help="All windows share same IP (default)")
    parser.add_argument("--no-same-ip", action="store_false", dest="same_ip", help="Each window gets separate IP session")
    parser.add_argument("--all-parallel", action="store_true", help="All workers in one batch session (single IP)")
    parser.add_argument("--no-vnc", action="store_true", help="Skip VNC server startup")
    parser.add_argument("-r", "--referrer", help="YouTube referrer URL")
    args = parser.parse_args()

    if args.no_vnc:
        os.environ["NO_VNC"] = "1"

    if args.interactive or not args.url:
        result = interactive_prompt()
        if result[-1]:  # is_parallel flag
            urls, windows, same_ips, views, rotate, no_vnc, all_parallel, _ = result
            rotate = rotate if not args.no_rotate else False
            orchestrate_parallel(urls, windows, same_ips, views, rotate, no_vnc, all_parallel)
        else:
            url, views, _, _, _, _ = result
            if args.referrer:
                os.environ["REFERRER_URL"] = args.referrer
            worker(url, views)
    else:
        if args.parallel:
            urls = args.url
            windows = [args.windows] * len(urls)
            same_ips = [args.same_ip] * len(urls)
            rotate = not args.no_rotate
            no_vnc = args.no_vnc
            all_parallel = args.all_parallel
            if args.referrer:
                os.environ["REFERRER_URL"] = args.referrer
            orchestrate_parallel(urls, windows, same_ips, args.views, rotate, no_vnc, all_parallel)
        else:
            url = args.url[0]
            views = args.views
            if args.referrer:
                os.environ["REFERRER_URL"] = args.referrer
            if args.no_rotate:
                os.environ["ROTATE_IP"] = "0"
            worker(url, views)

if __name__ == "__main__":
    main()
