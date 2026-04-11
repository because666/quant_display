@echo off
setlocal
set "ROOT=%~dp0"
echo Starting backend (FastAPI) ...
start "quant-backend" cmd /k cd /d "%ROOT%backend" ^&^& .\venv\Scripts\python.exe -m uvicorn src.main:app --reload

echo Starting frontend (Vite) ...
start "quant-frontend" cmd /k cd /d "%ROOT%frontend" ^&^& npm run dev

echo Done. Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:5173
endlocal
