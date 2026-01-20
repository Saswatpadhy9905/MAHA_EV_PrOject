#!/bin/bash
# Quick Start Script for EV Charging Station Simulation

echo "================================"
echo "EV Charging Simulation - Quick Start"
echo "================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first."
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python not found. Please install Python first."
        exit 1
    fi
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "✅ Python found: $($PYTHON_CMD --version)"

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
cd server
npm install
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd client/Opt-Frontend
npm install
cd ../..

# Check Python dependencies
echo "📦 Checking Python dependencies..."
$PYTHON_CMD -c "import networkx, numpy, matplotlib, scipy; print('✅ All Python dependencies found')" 2>/dev/null || {
    echo "⚠️  Installing Python dependencies..."
    pip install networkx numpy matplotlib scipy
}

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "To start the application:"
echo ""
echo "Terminal 1 - Start Backend:"
echo "  cd server"
echo "  npm start"
echo ""
echo "Terminal 2 - Start Frontend:"
echo "  cd client/Opt-Frontend"
echo "  npm run dev"
echo ""
echo "Then open http://localhost:5173 in your browser"
echo ""
