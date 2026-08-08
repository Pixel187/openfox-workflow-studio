@echo off
REM ============================================================
REM  Workflow Studio - Installation
REM  Cree le venv Python, installe les deps backend et frontend.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Workflow Studio - Installation
echo ============================================
echo.

REM ---------- Backend : venv + requirements ----------
echo [1/2] Backend (Python venv + requirements)...
if not exist ".venv" (
    echo   Creation du venv...
    python -m venv .venv
    if errorlevel 1 (
        echo   ERREUR : impossible de creer le venv. Python est-il installe ?
        pause
        exit /b 1
    )
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances Python.
    pause
    exit /b 1
)
echo [OK] Backend installe.
echo.

REM ---------- Frontend : npm install ----------
echo [2/2] Frontend (npm install)...
if not exist "web\node_modules" (
    pushd web
    call npm install
    if errorlevel 1 (
        popd
        echo [ERREUR] Echec de l'installation des dependances frontend.
        pause
        exit /b 1
    )
    popd
) else (
    echo [OK] node_modules deja present, installation ignoree.
)
echo [OK] Frontend installe.
echo.

echo ============================================
echo  Installation terminee.
echo  Lancez start.bat pour demarrer l'application.
echo ============================================
echo.
pause