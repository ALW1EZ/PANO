#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting PANO setup...${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}Installing/updating dependencies...${NC}"
    pip install -r requirements.txt
else
    echo -e "${BLUE}Installing required packages...${NC}"
    pip install PySide6 networkx qasync scipy folium aiofiles requests bs4 googlesearch-python geopy
    pip install -U g4f
fi

# Start PANO
echo -e "${GREEN}Starting PANO...${NC}"
python pano.py 