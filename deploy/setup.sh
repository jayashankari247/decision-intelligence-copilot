#!/bin/bash
# EC2 setup script — run once on a fresh Ubuntu 22.04 t3.large instance.
# Run as: bash setup.sh
set -e

APP_DIR="/home/ubuntu/decision-intelligence-copilot"
REPO="https://github.com/jayashankari247/decision-intelligence-copilot.git"

echo "==> [1/6] System packages"
sudo apt-get update -q
sudo apt-get install -y -q \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git curl unzip

echo "==> [2/6] Clone repository"
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO" "$APP_DIR"
else
    echo "     Repo already cloned — pulling latest"
    git -C "$APP_DIR" pull
fi

echo "==> [3/6] Python virtual environment + dependencies"
cd "$APP_DIR"
python3.11 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

echo "==> [4/6] Streamlit config (suppress browser launch + telemetry)"
mkdir -p "$APP_DIR/.streamlit"
cat > "$APP_DIR/.streamlit/config.toml" <<'TOML'
[server]
headless = true
port = 8501
address = "127.0.0.1"

[browser]
gatherUsageStats = false
TOML

echo "==> [5/6] systemd service"
sudo cp "$APP_DIR/deploy/copilot.service" /etc/systemd/system/copilot.service
sudo systemctl daemon-reload
sudo systemctl enable copilot

echo "==> [6/6] nginx"
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/copilot
sudo ln -sf /etc/nginx/sites-available/copilot /etc/nginx/sites-enabled/copilot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx

echo ""
echo "======================================================"
echo " Setup complete. Manual steps still required:"
echo ""
echo " 1. Upload .env to $APP_DIR/.env"
echo "    Must contain: ANTHROPIC_API_KEY and dataset paths"
echo ""
echo " 2. Upload dataset files to $APP_DIR/data/"
echo "    data/product_discovery/articles.csv"
echo "    data/product_discovery/transactions_train.csv"
echo "    data/customer_reviews/Womens Clothing E-Commerce Reviews.csv"
echo ""
echo " 3. Run one-time data setup:"
echo "    cd $APP_DIR"
echo "    venv/bin/python generate_inventory_snapshot.py"
echo "    venv/bin/python build_sqlite_db.py"
echo ""
echo " 4. Start services:"
echo "    sudo systemctl start copilot"
echo "    sudo systemctl start nginx"
echo ""
echo " 5. When your domain is ready, add the A record pointing"
echo "    to this Elastic IP, then run:"
echo "    sudo certbot --nginx -d your-domain.com"
echo "======================================================"
