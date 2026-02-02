#!/bin/bash

# EV Engine Initialization Script
# Simple, guided setup for EV Scout

set -e  # Exit on error

# Colors for better UX
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Header
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   EV Scout - Setup                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check Python
echo -e "${BLUE}[1/5]${NC} Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
echo ""

# Step 2: Create virtual environment
echo -e "${BLUE}[2/5]${NC} Setting up virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}! Virtual environment already exists, skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Step 3: Activate and install dependencies
echo -e "${BLUE}[3/5]${NC} Installing dependencies..."
source venv/bin/activate

# Upgrade pip quietly
pip install --upgrade pip -q

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Step 4: Configure API Key
echo -e "${BLUE}[4/5]${NC} Configuring API settings..."
if [ -f ".env" ]; then
    echo -e "${YELLOW}! .env file already exists${NC}"
    read -p "Do you want to update your API key? (y/N): " UPDATE_KEY
    if [[ ! $UPDATE_KEY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Skipping API key configuration${NC}"
    else
        rm .env
    fi
fi

if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}You need an API key from The Odds API${NC}"
    echo "Get one free at: https://the-odds-api.com/"
    echo ""
    read -p "Enter your Odds API key: " API_KEY

    if [ -z "$API_KEY" ]; then
        echo -e "${YELLOW}! No API key entered. You can add it later to .env${NC}"
        echo "ODDS_API_KEY=" > .env
    else
        echo "ODDS_API_KEY=$API_KEY" > .env
        echo -e "${GREEN}✓ API key saved to .env${NC}"
    fi
else
    echo -e "${GREEN}✓ Using existing .env configuration${NC}"
fi
echo ""

# Step 5: Initialize database
echo -e "${BLUE}[5/5]${NC} Initializing database..."
python3 -c "from src import db; db.initialize_db(); print('Database initialized successfully')" 2>&1 | grep -q "initialized successfully" && echo -e "${GREEN}✓ Database ready${NC}" || echo -e "${YELLOW}! Database may already be initialized${NC}"
echo ""

# Success message
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Setup Complete! 🚀            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Activate the environment:"
echo -e "     ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "  2. Run the dashboard:"
echo -e "     ${YELLOW}streamlit run dashboard.py${NC}"
echo ""
echo "  3. Click 'Refresh Market' to fetch odds"
echo ""
echo -e "${BLUE}Need help?${NC} Check BLUEPRINT.md for details"
echo ""
