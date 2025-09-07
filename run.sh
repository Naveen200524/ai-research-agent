#!/bin/bash

# AI Research Agent - Quick Start Script

echo "🔍 AI Research Agent - Starting..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your API keys"
    echo "   Required: GOOGLE_AI_API_KEY"
    echo "   Optional: HUGGINGFACE_API_KEY, TOGETHER_API_KEY, BRAVE_API_KEY"
    exit 1
fi

# Check for Docker
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker detected. Starting with Docker..."
    docker-compose up -d
    echo "✅ Started! Access at:"
    echo "   Frontend: http://localhost:8501"
    echo "   API Docs: http://localhost:8000/docs"
else
    echo "📦 Docker not found. Starting locally..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed."
        exit 1
    fi
    
    # Install dependencies
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
    playwright install chromium
    
    # Start backend
    echo "🚀 Starting backend..."
    cd backend
    python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to start
    echo "⏳ Waiting for backend to start..."
    sleep 5
    
    # Start frontend
    echo "🎨 Starting frontend..."
    cd frontend
    streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
    FRONTEND_PID=$!
    cd ..
    
    echo "✅ Started! Access at:"
    echo "   Frontend: http://localhost:8501"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop..."
    
    # Wait for interrupt
    trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
    wait
fi
