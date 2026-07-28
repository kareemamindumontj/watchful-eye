# Flipper Zero Setup Guide

## Quick Start

### 1. Prepare Your Files
Replace `YOUR_GITHUB_USERNAME` in `badusb-main.txt` with your actual GitHub username.

### 2. Copy to Flipper
```
Flipper SD Card/
└── badusb/
    └── WatchfulEye/
        ├── badusb-main.txt
        ├── badusb-nouac.txt
        └── README.txt
```

### 3. Use
1. Open BadUSB app on Flipper
2. Select "WatchfulEye"
3. Plug Flipper into target PC
4. Press center button
5. Click "Yes" on UAC (first time only)

## Files

| File | Description |
|------|-------------|
| `badusb-main.txt` | Main script - requires UAC click |
| `badusb-nouac.txt` | Alternative - no UAC required |
| `README.txt` | Quick reference for Flipper |

## What Gets Installed

- **Tailscale VPN** - For remote access
- **Python 3.11** - Runtime for agent
- **Watchful Eye Agent** - Remote management service
- **SYSTEM Service** - Auto-starts on boot, runs with full admin

## After Installation

The agent will:
1. Start automatically
2. Connect to your Raspberry Pi via Tailscale
3. Be visible in your dashboard
4. Accept remote commands

## Troubleshooting

**Script doesn't run:**
- Make sure BadUSB is enabled in Flipper settings
- Check the .txt file is in the correct SD card path

**UAC doesn't appear:**
- Some PCs have UAC disabled - script will run directly
- If blocked, try the no-UAC version

**Agent not connecting:**
- Ensure Tailscale is connected on both devices
- Check Pi server is running
- Verify agent service is running: `sc query WatchfulEye`

## Uninstall

Run `C:\ProgramData\WatchfulEye\uninstall.bat` as admin, or:
```
net stop WatchfulEye
sc delete WatchfulEye
rmdir /s /q "C:\ProgramData\WatchfulEye"
```
