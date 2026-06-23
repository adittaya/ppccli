#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────────────────────
# ppccli — one-command environment installer
# ────────────────────────────────────────────────────────────
# Usage:
#   curl -sL https://raw.githubusercontent.com/adittaya/ppccli/main/setup.sh | bash
#   # or
#   git clone https://github.com/adittaya/ppccli.git && cd ppccli && bash setup.sh
#
# What it does:
#   1. Installs system packages (chromium, chromedriver, Xvfb, x11vnc, python3, pip)
#   2. Installs Python dependencies (selenium, requests)
#   3. Creates /usr/local/bin/ppccli symlink
#   4. Verifies everything works
# ────────────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PPCCLI="$REPO_DIR/ppccli.py"

# ── Color helpers ──────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[ppccli]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

# ── Ensure script is inside a git clone ────────────────────
if [ ! -f "$PPCCLI" ]; then
    err "ppccli.py not found in $REPO_DIR"
    info "Clone the repo first:"
    info "  git clone https://github.com/adittaya/ppccli.git && cd ppccli && bash setup.sh"
    exit 1
fi

# ── Root check (we need sudo for system packages) ──────────
SUDO=""
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        err "Please run as root or install sudo"
        exit 1
    fi
fi

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     ppccli — Environment Setup       ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── Detect OS / package manager ────────────────────────────
install_system_pkg() {
    if command -v apt &>/dev/null; then
        $SUDO apt update -qq && $SUDO apt install -y -qq "$@"
    elif command -v dnf &>/dev/null; then
        $SUDO dnf install -y -q "$@"
    elif command -v yum &>/dev/null; then
        $SUDO yum install -y -q "$@"
    elif command -v pacman &>/dev/null; then
        $SUDO pacman -S --noconfirm "$@"
    elif command -v apk &>/dev/null; then
        $SUDO apk add --no-cache "$@"
    else
        err "No supported package manager found (apt/dnf/yum/pacman/apk)"
        info "Install these manually: python3, python3-pip, chromium, chromedriver, Xvfb, x11vnc"
        exit 1
    fi
}

# ── Platform-specific package names ────────────────────────
PY_PKG="python3"
PIP_PKG="python3-pip"
XVFB_PKG="xvfb"
X11VNC_PKG="x11vnc"

if command -v apt &>/dev/null; then
    CHROME_PKG="chromium-browser chromium-chromedriver"
    # Debian 12+ / Ubuntu 24.04+ use chromium and chromium-driver separately
    if apt-cache show chromium-driver &>/dev/null 2>&1; then
        CHROME_PKG="chromium chromium-driver"
    fi
elif command -v dnf &>/dev/null || command -v yum &>/dev/null; then
    CHROME_PKG="chromium chromedriver"
    XVFB_PKG="xorg-x11-server-Xvfb"
    X11VNC_PKG="x11vnc"
elif command -v pacman &>/dev/null; then
    CHROME_PKG="chromium chromedriver"
    XVFB_PKG="xorg-server-xvfb"
    X11VNC_PKG="x11vnc"
elif command -v apk &>/dev/null; then
    CHROME_PKG="chromium chromium-chromedriver"
    XVFB_PKG="xvfb"
    X11VNC_PKG="x11vnc"
    PY_PKG="python3"
    PIP_PKG="py3-pip"
fi

# ── Step 1: system packages ────────────────────────────────
info "Installing system packages (chromium, chromedriver, Xvfb, x11vnc, python3, pip)..."
install_system_pkg $PY_PKG $PIP_PKG $CHROME_PKG $XVFB_PKG $X11VNC_PKG 2>&1 | tail -3
ok "System packages installed"

# ── Step 2: Python dependencies ────────────────────────────
info "Installing Python packages (selenium, requests)..."
$SUDO pip3 install --break-system-packages -q selenium requests 2>/dev/null \
    || $SUDO pip3 install -q selenium requests 2>/dev/null \
    || pip3 install --user -q selenium requests
ok "Python packages installed"

# ── Step 3: symlink ────────────────────────────────────────
info "Creating /usr/local/bin/ppccli symlink..."
$SUDO ln -sf "$PPCCLI" /usr/local/bin/ppccli
$SUDO chmod +x "$PPCCLI"
ok "Symlink created — run 'ppccli --help' anytime"

# ── Step 4: verify chromium + chromedriver ─────────────────
info "Verifying installation..."
CHROME_OK=false; DRIVER_OK=false
CHROME_BINS=("chromium" "chromium-browser" "chromium/chromium")
for b in "${CHROME_BINS[@]}"; do
    if command -v "$(basename "$b")" &>/dev/null || [ -x "/usr/bin/$b" ] || [ -x "/usr/lib/$b" ]; then
        CHROME_OK=true; break
    fi
done
$CHROME_OK && ok "Chromium found" || warn "Chromium binary not found in PATH (may still work via chromedriver)"

DRIVER_PATHS=("chromedriver" "/usr/bin/chromedriver" "/usr/lib/chromium-browser/chromedriver" "/usr/lib/chromium/chromedriver")
for d in "${DRIVER_PATHS[@]}"; do
    if command -v "$d" &>/dev/null || [ -x "$d" ]; then
        DRIVER_OK=true; break
    fi
done
$DRIVER_OK && ok "Chromedriver found" || warn "Chromedriver not found in PATH — check installation"

if command -v Xvfb &>/dev/null; then ok "Xvfb found"; else warn "Xvfb not found"; fi
if command -v x11vnc &>/dev/null; then ok "x11vnc found"; else warn "x11vnc not found"; fi
if command -v python3 &>/dev/null; then ok "Python 3 found"; else err "Python 3 not found"; fi

# ── Step 5: test import ────────────────────────────────────
info "Testing Python imports..."
if python3 -c "from selenium import webdriver; print('selenium', end='')" 2>/dev/null; then
    ok "selenium import OK"
else
    err "selenium import failed — run: pip3 install selenium"
fi
if python3 -c "import requests; print('requests')" 2>/dev/null; then
    ok "requests import OK"
else
    warn "requests import failed — run: pip3 install requests"
fi

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║  Setup complete!                     ║"
echo "  ║                                      ║"
echo "  ║  Run: ppccli -i                     ║"
echo "  ║                                      ║"
echo "  ║  Or: ppccli -i --no-vnc             ║"
echo "  ║      (no VNC, headless)              ║"
echo "  ║                                      ║"
echo "  ║  For IP rotation: see               ║"
echo "  ║  droid_ui/setup_guide.md             ║"
echo "  ║  and macrodroid_airplane.md          ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
