#!/usr/bin/env bash
# ==============================================================================
# SentinelGIS - Automated Ubuntu VPS Deployment Script
# Targets: Ubuntu 20.04 / 22.04 / 24.04 LTS
# Sets up: Nginx Reverse Proxy + Systemd Service + Python Virtualenv + React Build
# ==============================================================================

set -e

# Color helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   SentinelGIS - Production Ubuntu VPS Setup        ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Root check
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Please run as root or with sudo:${NC} sudo bash $0"
  exit 1
fi

# Deployment settings: override any of these in the environment, e.g.
#   sudo SERVER_NAME=sentinel.example.com APP_PORT=9000 bash deploy/setup_vps.sh
INSTALL_DIR="${INSTALL_DIR:-/var/www/sentinelgis}"
APP_PORT="${APP_PORT:-8000}"
APP_USER="${APP_USER:-www-data}"
SERVER_NAME="${SERVER_NAME:-_}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-*}"
MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-25}"
NODE_MAJOR="${NODE_MAJOR:-20}"
# Each worker loads the model into memory; (2 x cores) + 1 is the Gunicorn rule of thumb
WORKERS="${WORKERS:-$(( $(nproc) * 2 + 1 ))}"

# Fill the __PLACEHOLDERS__ of a deploy template: render_template <src> <dest>
render_template() {
    sed -e "s|__INSTALL_DIR__|${INSTALL_DIR}|g" \
        -e "s|__APP_PORT__|${APP_PORT}|g" \
        -e "s|__APP_USER__|${APP_USER}|g" \
        -e "s|__SERVER_NAME__|${SERVER_NAME}|g" \
        -e "s|__ALLOWED_ORIGINS__|${ALLOWED_ORIGINS}|g" \
        -e "s|__MAX_UPLOAD_MB__|${MAX_UPLOAD_MB}|g" \
        -e "s|__WORKERS__|${WORKERS}|g" \
        "$1" > "$2"
}

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 2. Update System Packages
echo -e "\n${BLUE}📦 Step 1: Updating system packages and installing prerequisites...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv nginx git curl ufw

# Install Node.js LTS if node is not installed
if ! command -v node &> /dev/null; then
    echo -e "${BLUE}📦 Installing Node.js ${NODE_MAJOR} LTS...${NC}"
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
    apt-get install -y nodejs
fi
echo -e "${GREEN}✓ Python: $(python3 --version), Node: $(node --version)${NC}"

# 3. Copy or clone project files to /var/www/sentinelgis
echo -e "\n${BLUE}📂 Step 2: Setting up project in ${INSTALL_DIR}...${NC}"
if [ "$CURRENT_DIR" != "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    echo "Copying files from $CURRENT_DIR to $INSTALL_DIR..."
    cp -r "$CURRENT_DIR/." "$INSTALL_DIR/"
fi

cd "$INSTALL_DIR"

# 4. Build React Frontend
echo -e "\n${BLUE}⚛️  Step 3: Building React Production Bundle...${NC}"
cd "$INSTALL_DIR/frontend"
npm install --legacy-peer-deps
npm run build
echo -e "${GREEN}✓ Frontend build generated in $INSTALL_DIR/frontend/build${NC}"

# 5. Setup Python Virtual Environment & Install Dependencies
echo -e "\n${BLUE}🐍 Step 4: Configuring Python Virtualenv & ML Dependencies...${NC}"
cd "$INSTALL_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
echo -e "${GREEN}✓ Backend dependencies installed successfully.${NC}"

# 6. Set Permissions
echo -e "\n${BLUE}🔒 Step 5: Setting directory permissions for ${APP_USER}...${NC}"
chown -R "${APP_USER}:${APP_USER}" "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

# 7. Configure Systemd Service
echo -e "\n${BLUE}⚙️  Step 6: Installing Systemd Service...${NC}"
render_template "$INSTALL_DIR/deploy/sentinelgis.service" /etc/systemd/system/sentinelgis.service
systemctl daemon-reload
systemctl enable sentinelgis
systemctl restart sentinelgis

# Check service status
if systemctl is-active --quiet sentinelgis; then
    echo -e "${GREEN}✓ sentinelgis.service is ACTIVE and running on 127.0.0.1:${APP_PORT}${NC}"
else
    echo -e "${RED}⚠️  sentinelgis.service failed to start. Check logs with: journalctl -u sentinelgis -n 50${NC}"
fi

# 8. Configure Nginx
echo -e "\n${BLUE}🌐 Step 7: Configuring Nginx Reverse Proxy...${NC}"
render_template "$INSTALL_DIR/deploy/nginx.conf" /etc/nginx/sites-available/sentinelgis
ln -sf /etc/nginx/sites-available/sentinelgis /etc/nginx/sites-enabled/sentinelgis

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi

# Test and reload Nginx
nginx -t
systemctl restart nginx
echo -e "${GREEN}✓ Nginx successfully configured and reloaded.${NC}"

# 9. Firewall (UFW)
if ufw status | grep -q "Status: active"; then
    echo -e "\n${BLUE}🛡️  Opening ports 80 and 443 in UFW...${NC}"
    ufw allow 'Nginx Full'
fi

# 10. Done!
echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete! SentinelGIS is now LIVE!     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Access your application at: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"
echo -e "\n${BLUE}Helpful Commands:${NC}"
echo -e "  • Check Backend Status: ${GREEN}sudo systemctl status sentinelgis${NC}"
echo -e "  • View Backend Logs:    ${GREEN}sudo journalctl -u sentinelgis -f${NC}"
echo -e "  • Restart Backend:      ${GREEN}sudo systemctl restart sentinelgis${NC}"
echo -e "  • Test Nginx Config:    ${GREEN}sudo nginx -t${NC}"
echo -e "\n${BLUE}To enable free SSL HTTPS (Recommended):${NC}"
echo -e "  sudo apt install -y certbot python3-certbot-nginx"
echo -e "  sudo certbot --nginx -d yourdomain.com"
