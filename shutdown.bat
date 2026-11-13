@echo off
setlocal
set "ROOT=%~dp0"
set "PORT=5000"
for /f "tokens=1,* delims==" %%A in ('findstr /b "HELPDESK_PORT=" "%ROOT%.env" 2^>nul') do set "PORT=%%B"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$root = '%ROOT%'; $listeners = Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; $stopped = $false; foreach ($listener in $listeners) { $process = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $listener.OwningProcess); if ($process.CommandLine -and $process.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and $process.CommandLine -match 'backend[\\/]+app\.py') { Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop; Write-Output 'Campus Helpdesk stopped.'; $stopped = $true } }; if (-not $stopped) { Write-Output 'No Campus Helpdesk process for this project was found on port %PORT%.' }"
if errorlevel 1 (
    echo Could not stop the helpdesk. Try running shutdown.bat with the same permissions used to start it.
    pause
    exit /b 1
)
endlocal
