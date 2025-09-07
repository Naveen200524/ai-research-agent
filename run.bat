@echo off
echo AI Research Agent - Starting...

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found. Creating from template...
    copy .env.example .env
    echo Please edit .env and add your API keys
    echo Required: GOOGLE_AI_API_KEY
    echo Optional: HUGGINGFACE_API_KEY, BRAVE_API_KEY
    pause
    exit /b 1
)

REM Check for Docker
where docker >nul 2>nul
if %errorlevel%==0 (
    echo Docker detected. Starting with Docker...
    docker-compose up -d
    echo Started! Access at:
    echo   Frontend: http://localhost:8501
    echo   API Docs: http://localhost:8000/docs
) else (
    echo Docker not found. Starting locally...
    
    REM Check Python
    where python >nul 2>nul
    if %errorlevel%==1 (
        echo ERROR: Python is required but not installed.
        pause
        exit /b 1
    )
    
    REM Install dependencies
    echo Installing dependencies...
    pip install -r requirements.txt
    playwright install chromium
    
    REM Start backend
    echo Starting backend...
    start /B cmd /c "cd backend && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
    
    REM Wait a moment
    timeout /t 5 /nobreak >nul
    
    REM Start frontend
    echo Starting frontend...
    start /B cmd /c "cd frontend && streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
    
    echo Started! Access at:
    echo   Frontend: http://localhost:8501
    echo   API Docs: http://localhost:8000/docs
    echo.
    echo Press any key to stop...
    pause >nul
    
    REM Kill processes
    taskkill /F /IM python.exe >nul 2>nul
)
