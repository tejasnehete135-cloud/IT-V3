@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "PORT=5000"
set "LM_STUDIO_EXE=C:\Program Files\LM Studio\LM Studio.exe"

if exist "%ROOT%.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
        if /I "%%A"=="HELPDESK_PORT" set "PORT=%%B"
        if /I "%%A"=="LM_STUDIO_EXE" set "LM_STUDIO_EXE=%%B"
    )
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$root = '%ROOT%'; $port = '%PORT%'; $lmStudio = '%LM_STUDIO_EXE%'; $selfPid = $PID; $projectProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessId -ne $selfPid -and $_.CommandLine -and $_.CommandLine.IndexOf($root, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and $_.CommandLine -match 'backend[\\/]+app\.py' }; if ($projectProcesses) { foreach ($process in $projectProcesses) { Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue; Write-Output 'Campus Helpdesk stopped.' } } else { Write-Output ('No Campus Helpdesk process for this project was found on port ' + $port + '.') }; $lmProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -and [string]::Equals($_.ExecutablePath, $lmStudio, [System.StringComparison]::OrdinalIgnoreCase) }; if ($lmProcesses) { foreach ($process in $lmProcesses) { Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue; Write-Output 'LM Studio stopped.' } } else { Write-Output 'LM Studio was not running.' }"

if errorlevel 1 (
    echo Could not stop the helpdesk or LM Studio. Try running shutdown.bat with the same permissions used to start it.
    pause
    exit /b 1
)

endlocal
