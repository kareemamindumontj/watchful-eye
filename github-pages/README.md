# Watchful Eye - GitHub Pages Dashboard

A mobile-friendly web dashboard for managing your devices remotely.

## Setup

1. **Enable GitHub Pages:**
   - Go to your repository Settings → Pages
   - Source: Deploy from branch
   - Branch: main (or master)
   - Folder: /github-pages
   - Click Save

2. **First Time Setup:**
   - Open the site on your phone/laptop
   - Create a password (this will be required to log in)
   - Go to Settings and enter your Raspberry Pi's Tailscale IP
   - Save settings

3. **Pin to Home Screen:**
   - **iOS:** Tap Share button → Add to Home Screen
   - **Android:** Tap menu (⋮) → Add to Home Screen or Install App

4. **Access from anywhere:**
   - The site works as long as your Pi server is running
   - Uses same Tailscale network as desktop app
   - Same password as desktop app

## Features

- View all devices and their status
- Remote screen control (view + mouse/keyboard)
- Live microphone listening
- File browser
- Command execution
- Mining control
- Admin account creation

## Security

- Password protection (stored locally in browser)
- Same credentials as desktop app
- Works over Tailscale VPN

## Troubleshooting

- If "No devices found", check Pi server is running
- If can't connect, verify Pi IP in Settings
- For offline access, the app caches assets automatically
