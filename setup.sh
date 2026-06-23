#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# ppccli — Enterprise one-command environment installer
# ──────────────────────────────────────────────────────────────
# Usage:
#   curl -sL https://raw.githubusercontent.com/adittaya/ppccli/main/setup.sh | bash
#   bash <(curl -sL https://git.io/ppccli-setup)
#   git clone https://github.com/adittaya/ppccli.git && cd ppccli && bash setup.sh
#
# Exit codes:
#   0 — success
#   1 — prerequisite failure (no repo, no root)
#   2 — system package installation failed
#   3 — Python dependency installation failed
#   4 — symlink creation failed
#   5 — verification failed
# ──────────────────────────────────────────────────────────────
set -euo pipefail

APP="ppccli"
LOG="/tmp/ppccli-setup-$(date +%s).log"
REPO_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "/root/ppccli")"
PPCCLI="$REPO_DIR/ppccli.py"

# ── Trap handler (enterprise) ────────────────────────────────
cleanup() {
    local exit_code=$?
    local line_no=$1
    if [ $exit_code -ne 0 ]; then
        echo -e "\n\033[0;31m[✗]${NC} Setup failed at line ${line_no} (exit code ${exit_code})"
        echo -e "  \033[0;36m[>]${NC} Full log: ${LOG}"
        echo -e "  \033[0;36m[>]${NC} Run 'tail -50 ${LOG}' to see what went wrong"
        echo ""
    fi
}
trap 'cleanup $LINENO' EXIT

# ── Redirect all output to log (while still showing to user) ─
exec > >(tee -ia "$LOG") 2>&1

# ── Color helpers (ANSI) ─────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${CYAN}[${APP}]${NC} $1"; }
ok()    { echo -e "  ${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "  ${YELLOW}[!]${NC} $1"; }
err()   { echo -e "  ${RED}[✗]${NC} $1"; fail=1; }
step()  { echo -e "\n${BOLD}── $1 ──${NC}"; }
header(){ echo -e "${BOLD}$1${NC}"; }

# ──────────────────────────────────────────────────────────────
# STEP 0: Prerequisites
# ──────────────────────────────────────────────────────────────
header "
  ╔══════════════════════════════════════════════════╗
  ║           ppccli — Environment Setup             ║
  ║     Automated installer v2.0 (enterprise)        ║
  ╚══════════════════════════════════════════════════╝
"

fail=0

# 0a — Verify ppccli.py exists
step "Checking prerequisites"
info "Repository: ${REPO_DIR}"
if [ ! -f "$PPCCLI" ]; then
    err "ppccli.py not found at ${PPCCLI}"
    info "Clone the repo first:"
    info "  git clone https://github.com/adittaya/ppccli.git && cd ppccli && bash setup.sh"
    info "  curl -sL https://raw.githubusercontent.com/adittaya/ppccli/main/setup.sh | bash"
    exit 1
fi
ok "Found ppccli.py (${PPCCLI})"

# 0b — Network check
info "Checking internet connectivity..."
if ! timeout 10 curl -sf https://ipinfo.io/ip >/dev/null 2>&1; then
    warn "No internet connection detected"
    warn "Package installation may fail — continuing anyway"
else
    ok "Internet reachable"
fi

# 0c — Disk space
AVAIL_KB=$(df /usr --output=avail 2>/dev/null | tail -1 || echo 0)
if [ "$AVAIL_KB" -lt 500000 ] 2>/dev/null; then
    warn "Low disk space (${AVAIL_KB}KB available) — installation may fail"
else
    ok "Disk space adequate"
fi

# 0d — Root / sudo
SUDO=""
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
        info "Using sudo for system packages"
    else
        err "sudo not found. Run as root or install sudo: apt install sudo"
        exit 1
    fi
fi

# 0e — OS / package manager detection
PKG_MANAGER=""
PKG_UPDATE=""
PKG_INSTALL=""
if command -v apt &>/dev/null; then
    PKG_MANAGER="apt"
    PKG_UPDATE="$SUDO apt update -qq"
    PKG_INSTALL="$SUDO apt install -y -qq"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
    PKG_UPDATE="$SUDO dnf makecache -q"
    PKG_INSTALL="$SUDO dnf install -y -q"
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
    PKG_UPDATE="$SUDO yum makecache -q"
    PKG_INSTALL="$SUDO yum install -y -q"
elif command -v pacman &>/dev/null; then
    PKG_MANAGER="pacman"
    PKG_UPDATE="$SUDO pacman -Sy"
    PKG_INSTALL="$SUDO pacman -S --noconfirm"
elif command -v apk &>/dev/null; then
    PKG_MANAGER="apk"
    PKG_UPDATE="$SUDO apk update"
    PKG_INSTALL="$SUDO apk add --no-cache"
elif command -v zypper &>/dev/null; then
    PKG_MANAGER="zypper"
    PKG_UPDATE="$SUDO zypper refresh"
    PKG_INSTALL="$SUDO zypper install -y"
elif command -v xbps-install &>/dev/null; then
    PKG_MANAGER="xbps"
    PKG_UPDATE="$SUDO xbps-install -Su"
    PKG_INSTALL="$SUDO xbps-install -y"
else
    err "No supported package manager found (apt/dnf/yum/pacman/apk/zypper/xbps)"
    info "Install these manually: python3, python3-pip, chromium, chromedriver, Xvfb, x11vnc"
    exit 1
fi
ok "Package manager: ${PKG_MANAGER}"

# ── Platform-specific package names ─────────────────────────
PY_PKG="python3"
PIP_PKG="python3-pip"
XVFB_PKG="xvfb"
X11VNC_PKG="x11vnc"

case "$PKG_MANAGER" in
    apt)
        CHROME_PKG="chromium-browser chromium-chromedriver"
        if apt-cache show chromium-driver &>/dev/null 2>&1; then
            CHROME_PKG="chromium chromium-driver"
        fi
        if apt-cache show chromium-browser &>/dev/null 2>&1; then
            CHROME_PKG="chromium-browser chromium-chromedriver"
        fi
        ;;
    dnf|yum)
        CHROME_PKG="chromium chromedriver"
        XVFB_PKG="xorg-x11-server-Xvfb"
        X11VNC_PKG="x11vnc"
        PIP_PKG="python3-pip"
        ;;
    pacman)
        CHROME_PKG="chromium chromedriver"
        XVFB_PKG="xorg-server-xvfb"
        X11VNC_PKG="x11vnc"
        PIP_PKG="python-pip"
        ;;
    apk)
        CHROME_PKG="chromium chromium-chromedriver"
        XVFB_PKG="xvfb"
        X11VNC_PKG="x11vnc"
        PIP_PKG="py3-pip"
        PY_PKG="python3"
        ;;
    zypper)
        CHROME_PKG="chromium chromedriver"
        XVFB_PKG="xorg-x11-server-Xvfb"
        X11VNC_PKG="x11vnc"
        PIP_PKG="python3-pip"
        ;;
    xbps)
        CHROME_PKG="chromium chromedriver"
        XVFB_PKG="xvfb"
        X11VNC_PKG="x11vnc"
        PIP_PKG="python3-pip"
        ;;
esac

# ── Helper: is a package already installed? ─────────────────
pkg_installed() {
    case "$PKG_MANAGER" in
        apt)    dpkg -s "$1" &>/dev/null;;
        dnf|yum) rpm -q "$1" &>/dev/null;;
        pacman) pacman -Qi "$1" &>/dev/null;;
        apk)    apk info -e "$1" &>/dev/null;;
        zypper) rpm -q "$1" &>/dev/null;;
        xbps)   xbps-query "$1" &>/dev/null;;
        *)      return 1;;
    esac
}

# ── Helper: install with retry ──────────────────────────────
install_pkg() {
    local pkg_name="$1"
    if pkg_installed "$pkg_name" 2>/dev/null; then
        ok "${pkg_name} already installed"
        return 0
    fi
    for attempt in 1 2 3; do
        info "Installing ${pkg_name} (attempt ${attempt}/3)..."
        if $PKG_INSTALL "$pkg_name" 2>>"$LOG"; then
            # Verify it actually got installed
            if pkg_installed "$pkg_name" 2>/dev/null; then
                ok "${pkg_name} installed"
                return 0
            fi
        fi
        if [ $attempt -lt 3 ]; then
            warn "Retrying in 3 seconds..."
            sleep 3
            $PKG_UPDATE &>/dev/null || true
        fi
    done
    err "Failed to install ${pkg_name} after 3 attempts"
    info "Manual: ${PKG_INSTALL} ${pkg_name}"
    return 1
}

# ──────────────────────────────────────────────────────────────
# STEP 1: System packages
# ──────────────────────────────────────────────────────────────
step "Installing system packages"

info "Updating package index..."
$PKG_UPDATE &>/dev/null || warn "Package index update failed (non-fatal)"

ALL_PKGS="$PY_PKG $PIP_PKG $CHROME_PKG $XVFB_PKG $X11VNC_PKG"
INSTALL_FAILED=0
for pkg in $ALL_PKGS; do
    install_pkg "$pkg" || INSTALL_FAILED=1
done

if [ "$INSTALL_FAILED" -eq 1 ]; then
    err "Some system packages failed to install (exit code 2)"
    info "Check 'tail -50 ${LOG}' for details"
    exit 2
fi
ok "All system packages installed"

# ──────────────────────────────────────────────────────────────
# STEP 2: Python dependencies
# ──────────────────────────────────────────────────────────────
step "Installing Python dependencies"

# Try multiple pip strategies (newer pip versions block --system)
pip_install() {
    # Strategy 1: system pip with --break-system-packages (pip>=21.3)
    if $SUDO python3 -m pip install --break-system-packages -q selenium requests 2>/dev/null; then
        return 0
    fi
    # Strategy 2: system pip without flag (older pip)
    if $SUDO python3 -m pip install -q selenium requests 2>/dev/null; then
        return 0
    fi
    # Strategy 3: user install as fallback
    if python3 -m pip install --user -q selenium requests 2>/dev/null; then
        return 0
    fi
    # Strategy 4: pip3 binary
    if $SUDO pip3 install --break-system-packages -q selenium requests 2>/dev/null; then
        return 0
    fi
    if $SUDO pip3 install -q selenium requests 2>/dev/null; then
        return 0
    fi
    return 1
}

if pip_install; then
    ok "Python packages installed"
else
    err "Failed to install Python packages (exit code 3)"
    info "Manual: pip3 install selenium requests"
    info "If you see 'externally-managed-environment' error:"
    info "  pip3 install --break-system-packages selenium requests"
    exit 3
fi

# Verify imports work
PY_OK=true
python3 -c "from selenium import webdriver; print('selenium OK')" 2>/dev/null || { PY_OK=false; err "selenium import failed"; }
python3 -c "import requests; print('requests OK')" 2>/dev/null || { PY_OK=false; warn "requests import failed (non-fatal)"; }
if ! $PY_OK; then
    err "Python imports failing — try: pip3 install --upgrade selenium requests"
    exit 3
fi

# ──────────────────────────────────────────────────────────────
# STEP 3: Symlink
# ──────────────────────────────────────────────────────────────
step "Creating command symlink"

SYMLINK_TARGET="/usr/local/bin/${APP}"

# Check if existing symlink points to the right place
if [ -L "$SYMLINK_TARGET" ] && [ "$(readlink "$SYMLINK_TARGET")" = "$PPCCLI" ]; then
    ok "Symlink already points to ${PPCCLI}"
elif [ -f "$SYMLINK_TARGET" ] || [ -L "$SYMLINK_TARGET" ]; then
    warn "Overwriting existing $(file "$SYMLINK_TARGET" 2>/dev/null || echo 'file')"
    $SUDO rm -f "$SYMLINK_TARGET"
    $SUDO ln -sf "$PPCCLI" "$SYMLINK_TARGET"
    ok "Symlink updated"
else
    # Ensure /usr/local/bin exists
    $SUDO mkdir -p /usr/local/bin
    $SUDO ln -sf "$PPCCLI" "$SYMLINK_TARGET"
    ok "Symlink created: ${SYMLINK_TARGET} → ${PPCCLI}"
fi

$SUDO chmod +x "$PPCCLI"

# Verify symlink
if command -v "$APP" &>/dev/null; then
    ok "Command '${APP}' resolves to $(command -v "$APP")"
else
    err "Symlink created but '${APP}' not found in PATH"
    info "Ensure /usr/local/bin is in your PATH, or run: export PATH=\$PATH:/usr/local/bin"
    exit 4
fi

# ──────────────────────────────────────────────────────────────
# STEP 4: Verification
# ──────────────────────────────────────────────────────────────
step "Verifying installation"

VERIFY_FAILED=0

# Chromium
CHROME_OK=false
for b in chromium chromium-browser; do
    if command -v "$b" &>/dev/null; then
        CHROME_OK=true
        ok "Chromium found: $(command -v "$b")"
        break
    fi
done
if ! $CHROME_OK; then
    for p in /usr/bin/chromium /usr/lib/chromium/chromium /snap/bin/chromium; do
        if [ -x "$p" ]; then
            CHROME_OK=true
            ok "Chromium found: ${p}"
            break
        fi
    done
fi
$CHROME_OK || { warn "Chromium binary not in PATH"; VERIFY_FAILED=1; }

# Chromedriver
DRIVER_OK=false
DRIVER_PATHS=(chromedriver /usr/bin/chromedriver /usr/lib/chromium-browser/chromedriver /usr/lib/chromium/chromedriver /snap/bin/chromedriver)
for d in "${DRIVER_PATHS[@]}"; do
    if command -v "$d" &>/dev/null || [ -x "$d" ]; then
        DRIVER_OK=true
        ok "Chromedriver found: $(command -v "$d" 2>/dev/null || echo "$d")"
        break
    fi
done
$DRIVER_OK || { warn "Chromedriver not in PATH — ppccli needs it to launch Chrome"; VERIFY_FAILED=1; }

# Version compatibility check
if $CHROME_OK && $DRIVER_OK; then
    CHROME_VER=$(chromium --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "?")
    DRIVER_VER=$(chromedriver --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "?")
    if [ "$CHROME_VER" != "?" ] && [ "$DRIVER_VER" != "?" ] && [ "${CHROME_VER%.*}" != "${DRIVER_VER%.*}" ]; then
        warn "Version mismatch: Chromium ${CHROME_VER} vs Chromedriver ${DRIVER_VER}"
        warn "This may cause WebDriver errors — reinstall both to match versions"
    else
        ok "Chromium ${CHROME_VER} / Chromedriver ${DRIVER_VER} (compatible)"
    fi
fi

# Xvfb
if command -v Xvfb &>/dev/null; then ok "Xvfb found"; else warn "Xvfb not found — required for headless display"; VERIFY_FAILED=1; fi

# x11vnc (optional)
if command -v x11vnc &>/dev/null; then ok "x11vnc found (optional, for VNC)"; else warn "x11vnc not found (optional)"; fi

# Python
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1)
    ok "Python: ${PY_VER}"
else
    err "Python 3 not found"
    VERIFY_FAILED=1
fi

# Script test
if python3 "$PPCCLI" --help &>/dev/null; then
    ok "ppccli.py --help runs successfully"
else
    err "ppccli.py --help failed"
    VERIFY_FAILED=1
fi

# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
step "Setup complete"

if [ "$VERIFY_FAILED" -eq 1 ]; then
    warn "Some optional components are missing — ppccli may still work"
    info "Check warnings above for details"
fi

# Show ppccli version / info
ppccli_version=$(python3 "$PPCCLI" --help 2>&1 | head -1 || echo "ppccli v?.?")

echo ""
echo "  ${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo "  ${BOLD}║          Setup complete!                     ║${NC}"
echo "  ${BOLD}║  ${ppccli_version}                ║${NC}"
echo "  ${BOLD}╠══════════════════════════════════════════════╣${NC}"
echo "  ${BOLD}║${NC}  Quick start:                                ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}    ppccli -i              Interactive mode   ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}    ppccli -i --no-vnc     No VNC (headless)  ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}                                            ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}  Parallel:                                    ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}    ppccli -p --all-parallel --no-vnc \\      ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}      -n 100 -w 1 \\                       ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}      -r \"https://youtu.be/...\" \\          ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}      \"https://arolinks.com/zREqi\" \\       ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}      \"https://vplink.in/MGIt8\"              ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}                                            ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}  IP rotation guides:                        ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}    droid_ui/setup_guide.md                  ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}    macrodroid_airplane.md                   ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}                                            ${BOLD}║${NC}"
echo "  ${BOLD}║${NC}  Full log: ${LOG}       ${BOLD}║${NC}"
echo "  ${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

if [ "$fail" -ne 0 ]; then
    warn "Completed with ${fail} non-fatal warnings"
fi

exit 0
