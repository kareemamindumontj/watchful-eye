#!/bin/bash

echo "========================================="
echo "  Watchful Eye Server Setup (Raspberry Pi)"
echo "========================================="
echo ""

echo "[1/6] Updating system..."
sudo apt update && sudo apt upgrade -y

echo ""
echo "[2/6] Installing Python dependencies..."
sudo apt install -y python3-pip python3-venv

echo ""
echo "[3/6] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "[4/6] Installing pip packages..."
pip install -r requirements.txt

echo ""
echo "[5/6] Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

echo ""
echo "[6/6] Creating systemd service..."
sudo tee /etc/systemd/system/watchful-eye.service > /dev/null <<EOF
[Unit]
Description=Watchful Eye Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable watchful-eye
sudo systemctl start watchful-eye

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Server is running on port 8000"
echo "Access at: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "Tailscale IP: $(tailscale ip -4)"
echo ""
echo "Service commands:"
echo "  sudo systemctl status watchful-eye"
echo "  sudo systemctl restart watchful-eye"
echo "  sudo systemctl stop watchful-eye"
echo ""
