WATCHFUL EYE - FLIPPER SETUP
=============================

FILES NEEDED:
- badusb-main.txt (rename to WatchfulEye.txt)

INSTALLATION:
1. Copy .txt to Flipper SD:/badusb/
2. Open BadUSB on Flipper
3. Select WatchfulEye
4. Plug Flipper into PC
5. Press center button
6. Click Yes on UAC prompt

WHAT IT DOES:
- Installs Tailscale VPN
- Installs Python 3.11
- Downloads Watchful Eye agent
- Registers as SYSTEM service
- Agent auto-starts on boot

AFTER INSTALL:
- Agent connects to your Pi
- Manage from desktop app or website
- No more interaction needed

TIPS:
- Works on Windows 10/11
- Requires internet connection
- First boot takes ~2 minutes
- Agent runs silently in background

UNINSTALL:
Run C:\ProgramData\WatchfulEye\uninstall.bat
