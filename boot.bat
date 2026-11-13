@echo off
setlocal
set "ROOT=%~dp0"
set "PORT=5000"
for /f "tokens=1,* delims==" %%A in ('findstr /b "HELPDESK_PORT=" "%ROOT%.env" 2^>nul') do set "PORT=%%B"

pushd "%ROOT%"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON=python"
        ) else (
            echo Python was not found. Install Python or create the project .venv.
            popd
            pause
            exit /b 1
        )
    )
)

curl.exe --silent --fail "http://127.0.0.1:%PORT%/api/health" >nul 2>nul
if not errorlevel 1 (
    echo Campus Helpdesk is already running at http://127.0.0.1:%PORT%/
    start "" "http://127.0.0.1:%PORT%/"
    popd
    exit /b 0
)

echo Starting Campus Helpdesk...
if exist ".venv\Scripts\python.exe" (
    start "Campus Helpdesk" /min "%PYTHON%" "%ROOT%backend\app.py"
) else (
    start "Campus Helpdesk" /min %PYTHON% "%ROOT%backend\app.py"
)

for /l %%I in (1,1,20) do (
    powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"
    curl.exe --silent --fail "http://127.0.0.1:%PORT%/api/health" >nul 2>nul
    if not errorlevel 1 (
        echo Campus Helpdesk is ready at http://127.0.0.1:%PORT%/
        start "" "http://127.0.0.1:%PORT%/"
        popd
        exit /b 0
    )
)

echo The helpdesk did not become ready. Check the Python window and dependencies.
popd
pause
exit /b 1
