#!/usr/bin/env bash
set -e

echo "=== native_automator setup ==="

echo ""
echo "1. Installing Python dependencies..."
pip3 install --quiet --upgrade pip 2>/dev/null || true
# No external deps needed — this project uses only stdlib

echo ""
echo "2. Checking project structure..."
ls -R automator/ scripts/ 2>/dev/null

echo ""
echo "3. Setup complete!"
echo ""
echo "What to do next:"
echo "  a) Open MacroDroid on your phone"
echo "  b) Run:  python3 setup_macros.py"
echo "     (follow the interactive guide to create 22 macros)"
echo "  c) Enable MacroDroid HTTP Server"
echo "     (Settings → HTTP Server → port 8580)"
echo "  d) Test: python3 scripts/test_connection.py"
echo "  e) Start automating! See scripts/ for examples."
echo ""
echo "Quick test:"
echo "  python3 -c \"from automator import Device; d=Device(); d.back()\""
echo ""
