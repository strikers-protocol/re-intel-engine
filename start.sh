#!/bin/bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN} ⬡  STRIKERS_PROTOCOL RE::INTEL v2.0${NC}"
echo -e "${CYAN} =========================================${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED} [ERROR] Python 3 not found. Install from https://python.org${NC}"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_VER" -lt 10 ]; then
    echo -e "${RED} [ERROR] Python 3.10+ required. Current: $(python3 --version)${NC}"
    exit 1
fi

# Create .env if missing
if [ ! -f .env ]; then
    echo -e "${YELLOW} [SETUP] Creating .env from template...${NC}"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW} !! IMPORTANT: Add your ANTHROPIC_API_KEY to .env !!${NC}"
    echo -e "${YELLOW} !! Get it from: https://console.anthropic.com    !!${NC}"
    echo ""
    echo -e "Open .env now? [y/N] \c"
    read -r ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
fi

# Virtual environment
if [ ! -d "venv" ]; then
    echo -e "${GREEN} [SETUP] Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Install
echo -e "${GREEN} [SETUP] Installing dependencies...${NC}"
pip install -r requirements.txt -q --disable-pip-version-check

# Dirs
mkdir -p uploads reports data

echo ""
echo -e "${CYAN} =========================================${NC}"
echo -e "${GREEN} ✓  Server: http://localhost:8000${NC}"
echo -e "${GREEN} ✓  API docs: http://localhost:8000/api/docs${NC}"
echo -e "${CYAN} =========================================${NC}"
echo ""

# Open browser
(sleep 2 && (xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null)) &

# Start
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
