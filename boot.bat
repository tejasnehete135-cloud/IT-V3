@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "PORT=5000"
set "LM_STUDIO_EXE=C:\Program Files\LM Studio\LM Studio.exe"
set "LM_STUDIO_MODEL=qwen/qwen3-4b"
set "LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1"
set "LMS=%USERPROFILE%\.lmstudio\bin\lms.exe"

if exist "%ROOT%.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
        if /I "%%A"=="HELPDESK_PORT" set "PORT=%%B"
        if /I "%%A"=="LM_STUDIO_EXE" set "LM_STUDIO_EXE=%%B"
        if /I "%%A"=="LM_STUDIO_MODEL" set "LM_STUDIO_MODEL=%%B"
        if /I "%%A"=="LM_STUDIO_BASE_URL" set "LM_STUDIO_BASE_URL=%%B"
    )
)

pushd "%ROOT%"
if not exist "%LM_STUDIO_EXE%" (
    echo LM Studio was not found at "%LM_STUDIO_EXE%".
    echo Update LM_STUDIO_EXE in .env to the installed LM Studio.exe path.
    popd
    pause
    exit /b 1
)

if not exist "%LMS%" (
    where lms.exe >nul 2>nul
    if not errorlevel 1 set "LMS=lms.exe"
)
if not exist "%LMS%" if /I not "%LMS%"=="lms.exe" (
    echo LM Studio's lms.exe CLI was not found.
    echo Install or update LM Studio, then try again.
    popd
    pause
    exit /b 1
)

echo Starting LM Studio...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$exe = '%LM_STUDIO_EXE%'; if (-not (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe })) { Start-Process -FilePath $exe }"
if errorlevel 1 (
    echo Could not start LM Studio.
    popd
    pause
    exit /b 1
)

echo Waiting for the LM Studio server...
"%LMS%" server status >nul 2>nul
if errorlevel 1 "%LMS%" server start
set "LM_SERVER_READY="
for /l %%I in (1,1,30) do (
    "%LMS%" server status >nul 2>nul
    if not errorlevel 1 set "LM_SERVER_READY=1"
    if defined LM_SERVER_READY goto :server_ready
    powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"
)
:server_ready
if not defined LM_SERVER_READY (
    echo LM Studio server did not start. Check LM Studio and try again.
    popd
    pause
    exit /b 1
)

echo Loading model %LM_STUDIO_MODEL%...
set "MODEL_LOAD_ATTEMPTS=0"
:load_model
"%LMS%" load "%LM_STUDIO_MODEL%" --yes
if not errorlevel 1 goto model_loaded
set /a MODEL_LOAD_ATTEMPTS+=1
if %MODEL_LOAD_ATTEMPTS% GEQ 6 goto model_load_failed
echo LM Studio is still initializing. Retrying model load in 5 seconds...
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 5"
goto load_model

:model_loaded
"%LMS%" ps | findstr /I /C:"%LM_STUDIO_MODEL%" >nul
if errorlevel 1 (
    echo LM Studio completed the load command, but the model is not listed as loaded.
    popd
    pause
    exit /b 1
)
echo Model %LM_STUDIO_MODEL% is loaded.
goto model_ready

:model_load_failed
echo Could not load model "%LM_STUDIO_MODEL%".
echo Confirm the model is downloaded in LM Studio and matches LM_STUDIO_MODEL in .env.
popd
pause
exit /b 1

:model_ready

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
