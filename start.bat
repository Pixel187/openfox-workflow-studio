@echo off
REM ============================================================
REM  Workflow Studio - Demarrage
REM  Lance le backend FastAPI (port 8765) et le frontend Vite
REM  (port 5173) en parallele, puis ouvre le navigateur.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Workflow Studio - Demarrage
echo ============================================
echo.

REM ---------- Verifications ----------
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] venv absent. Lancez install.bat d'abord.
    pause
    exit /b 1
)
if not exist "web\node_modules" (
    echo [ERREUR] dependances frontend absentes. Lancez install.bat d'abord.
    pause
    exit /b 1
)

REM ---------- Backend : uvicorn ----------
echo [1/2] Backend FastAPI  ->  http://127.0.0.1:8765
start "Workflow Studio - Backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765"
if errorlevel 1 (
    echo [ERREUR] Echec du lancement du backend.
    pause
    exit /b 1
)

REM ---------- Frontend : vite dev ----------
echo [2/2] Frontend Vite    ->  http://localhost:5173
start "Workflow Studio - Frontend" cmd /k "cd web && npm run dev"
if errorlevel 1 (
    echo [ERREUR] Echec du lancement du frontend.
    pause
    exit /b 1
)

REM ---------- Navigateur ----------
echo.
echo Ouverture du navigateur dans 3 secondes...
timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ============================================
echo  Application demarree.
echo   - Frontend : http://localhost:5173
echo   - Backend  : http://127.0.0.1:8765
echo  Fermez les fenetres "Workflow Studio - ..."
echo  pour arreter l'application.
echo ============================================
echo.
pause