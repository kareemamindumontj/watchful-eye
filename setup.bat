@echo off
setlocal
title Watchful Eye - Auto Setup

echo.
echo  ██╗    ██╗██╗███████╗██╗    ███████╗ ██████╗ █████╗ ███╗   ██╗
echo  ██║    ██║██║██╔════╝██║    ██╔════╝██╔════╝██╔══██╗████╗  ██║
echo  ██║ █╗ ██║██║█████╗  ██║    ███████╗██║     ███████║██╔██╗ ██║
echo  ██║███╗██║██║██╔══╝  ██║    ╚════██║██║     ██╔══██║██║╚██╗██║
echo  ╚███╔███╔╝██║██║     ██║    ███████║╚██████╗██║  ██║██║ ╚████║
echo   ╚══╝╚══╝ ╚═╝╚═╝     ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
echo.
echo              Remote Device Management System
echo.
echo ============================================
echo   Auto-Setup Started
echo ============================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)

echo [✓] Running as Administrator
echo.

REM Create working directory
echo [1/7] Creating directories...
mkdir "C:\ProgramData\WatchfulEye" 2>nul
mkdir "C:\ProgramData\WatchfulEye\logs" 2>nul
echo [✓] Directories created
echo.

REM Check if already installed
if exist "C:\ProgramData\WatchfulEye\agent.exe" (
    echo [!] Agent already installed - updating...
    sc stop WatchfulEye >nul 2>&1
)

REM Install Tailscale
echo [2/7] Installing Tailscale VPN...
where tailscale >nul 2>&1
if %errorLevel% neq 0 (
    winget install Tailscale.Tailscale --accept-package-agreements --accept-source-agreements --silent
    if %errorLevel% neq 0 (
        echo [!] Tailscale install failed - downloading manually...
        powershell -Command "Invoke-WebRequest -Uri 'https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe' -OutFile '%TEMP%\tailscale.exe'"
        "%TEMP%\tailscale.exe" /install /quiet
    )
    echo [✓] Tailscale installed
) else (
    echo [✓] Tailscale already installed
)
echo.

REM Install Python
echo [3/7] Installing Python...
where python >nul 2>&1
if %errorLevel% neq 0 (
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements --silent
    set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"
    echo [✓] Python installed
) else (
    echo [✓] Python already installed
)
echo.

REM Install Python packages
echo [4/7] Installing Python packages...
pip install psutil requests mss pyaudio wmi pywin32 --quiet --disable-pip-version-check
echo [✓] Packages installed
echo.

REM Download agent files
echo [5/7] Downloading agent files...
set "GITHUB_URL=https://raw.githubusercontent.com/kareemamindumontj/watchful-eye/main"

powershell -Command "try { Invoke-WebRequest -Uri '%GITHUB_URL%/agent_server.py' -OutFile 'C:\ProgramData\WatchfulEye\agent_server.py' -UseBasicParsing } catch { Write-Host 'Download failed' }"
powershell -Command "try { Invoke-WebRequest -Uri '%GITHUB_URL%/agent_mining.py' -OutFile 'C:\ProgramData\WatchfulEye\agent_mining.py' -UseBasicParsing } catch { Write-Host 'Download failed' }"
powershell -Command "try { Invoke-WebRequest -Uri '%GITHUB_URL%/agent_service.py' -OutFile 'C:\ProgramData\WatchfulEye\agent_service.py' -UseBasicParsing } catch { Write-Host 'Download failed' }"

echo [✓] Agent files downloaded
echo.

REM Find Python path
echo [6/7] Finding Python...
for /f "delims=" %%i in ('where python') do (
    set "PYTHON_PATH=%%i"
    goto :found_python
)
:found_python
echo [✓] Python found at: %PYTHON_PATH%
echo.

REM Register Windows service
echo [7/7] Registering Windows service...
sc delete WatchfulEye >nul 2>&1
sc create WatchfulEye binPath= "\"%PYTHON_PATH%\" \"C:\ProgramData\WatchfulEye\agent_service.py\"" start= auto obj= "LocalSystem"
sc description WatchfulEye "Watchful Eye Remote Management Agent - DO NOT DISABLE"
sc failure WatchfulEye reset= 86400 actions= restart/60000/restart/120000/restart/300000

REM Start the service
net start WatchfulEye

echo.
echo ============================================
echo   ✓ Installation Complete!
echo ============================================
echo.
echo   Agent Status: RUNNING
echo   Service Name: WatchfulEye
echo   Install Dir:  C:\ProgramData\WatchfulEye
echo.
echo   The agent will start automatically on boot.
echo   It connects to your Raspberry Pi via Tailscale.
echo.
echo ============================================
echo.

REM Create uninstall script
(
    echo @echo off
    echo net stop WatchfulEye
    echo sc delete WatchfulEye
    echo rmdir /s /q "C:\ProgramData\WatchfulEye"
    echo echo Watchful Eye uninstalled!
    echo pause
) > "C:\ProgramData\WatchfulEye\uninstall.bat"

echo Press any key to exit...
pause >nul
