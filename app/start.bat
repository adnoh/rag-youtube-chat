@echo off
setlocal EnableDelayedExpansion

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

REM ── Python deps via uv ──────────────────────────────────────────────────
echo Installing Python dependencies with uv...
pushd "%BACKEND_DIR%"
uv sync --all-extras
if errorlevel 1 (
    echo ERROR: uv sync failed. Is uv installed?
    popd
    exit /b 1
)
popd

REM ── Data directory ────────────────────────────────────────────────────────
if not exist "%BACKEND_DIR%\data" mkdir "%BACKEND_DIR%\data"

REM ── .env ──────────────────────────────────────────────────────────────────
if not exist "%SCRIPT_DIR%.env" (
    set ROOT_ENV=%SCRIPT_DIR%..\..\..\..\.env
    if exist "!ROOT_ENV!" (
        copy "!ROOT_ENV!" "%SCRIPT_DIR%.env" >nul
        echo Copied .env from !ROOT_ENV!
    )
)

REM ── Start FastAPI backend (skip if already running) ───────────────────────
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo Port 8000 already in use -- assuming FastAPI is already running.
) else (
    echo Starting FastAPI on port 8000...
    cd /d "%SCRIPT_DIR%"
    start "FastAPI Backend" cmd /c "uv --project %BACKEND_DIR% run uvicorn backend.main:app --reload --port 8000"
    REM Give backend a moment to start
    timeout /t 5 /nobreak >nul
)

REM ── Frontend ──────────────────────────────────────────────────────────────
if not exist "%FRONTEND_DIR%\node_modules" (
    echo Installing frontend dependencies with bun...
    cd /d "%FRONTEND_DIR%"
    bun install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies. Is bun installed?
        exit /b 1
    )
)

REM Check if port 5173 is already in use
netstat -ano | findstr ":5173 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo Port 5173 already in use -- assuming Vite is already running.
) else (
    echo Starting Vite dev server on port 5173...
    cd /d "%FRONTEND_DIR%"
    bun run dev
)
