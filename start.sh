#!/bin/bash

# QUANTUM MIND - Startup Script for Linux/Mac

echo ""
echo "============================================"
echo "   QUANTUM MIND v1.0 - Startup"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "[OK] Python 3 is installed: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[OK] Virtual environment created"
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "[INFO] Installing requirements..."
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install requirements"
    exit 1
fi

echo "[OK] Requirements installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found"
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo "[WARNING] Please edit .env and set your GOOGLE_API_KEY"
    echo ""
    read -p "Edit .env now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        else
            echo "Please edit .env manually"
        fi
    fi
fi

# Start the application
echo ""
echo "[INFO] Starting QUANTUM MIND..."
echo ""

python main.py
