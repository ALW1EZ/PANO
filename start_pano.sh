#!/bin/bash

echo "Checking PANO version..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Git is not installed. Please install git first."
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo "Not in a git repository. Please clone PANO properly."
    exit 1
fi

# Make sure we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Switching to main branch..."
    git checkout main
    if [ $? -ne 0 ]; then
        echo "Failed to switch to main branch. Please check your git status."
        exit 1
    fi
fi

# Fetch the latest changes without merging
git fetch origin main

# Get current and latest versions
CURRENT_VERSION=$(git rev-parse HEAD)
LATEST_VERSION=$(git rev-parse origin/main)

if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "Your PANO version is outdated."
    echo "Current version: ${CURRENT_VERSION:0:7}"
    echo "Latest version: ${LATEST_VERSION:0:7}"
    read -p "Would you like to update? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Updating PANO..."
        git pull origin main
        if [ $? -ne 0 ]; then
            echo "Update failed. Please resolve any conflicts and try again."
            exit 1
        fi
        echo "Update successful!"
    else
        echo "Continuing with current version..."
    fi
else
    echo "PANO is up to date."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start PANO
echo "Starting PANO..."
python3 pano.py 