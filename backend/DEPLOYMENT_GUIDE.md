# Digital Ocean Droplet Deployment Guide

## 📋 Prerequisites

Before you begin, ensure you have:
- Digital Ocean droplet running Ubuntu 20.04+ or similar Linux distro
- SSH access to the droplet
- Your GitHub repository URL
- OpenAI API key

## 🚀 Step-by-Step Deployment

### 1. Initial Server Setup

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Python 3.9+ (if not already installed)
sudo apt install python3 python3-pip python3-venv -y

# Verify Python version (should be 3.9+)
python3 --version

# Install git (if not already installed)
sudo apt install git -y

# Install required system dependencies for Python packages
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y
```

<!--  Checkout branch deploy -->
git bran

### 2. Clone the Repository

```bash
# Navigate to your preferred directory
cd ~

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git hackathon

# Navigate into the project
cd hackathon/backend
```

ssh scarfacedishvalan@167.172.198.36

### 3. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Install production ASGI server
pip install gunicorn uvicorn[standard]
```

### 5. Configure Environment Variables

```bash
# Create .env file
nano .env

# Add the following (press Ctrl+X, then Y to save):
OPENAI_API_KEY=your_openai_api_key_here
```

Or export directly:
```bash
export OPENAI_API_KEY="YOUR_KEY"

# To make it permanent, add to ~/.bashrc
echo 'export OPENAI_API_KEY=your_openai_api_key_here' >> ~/.bashrc
source ~/.bashrc
```

### 6. Create Required Data Directories

```bash
# Ensure data directories exist
mkdir -p data/agent_audits
mkdir -p data/bl_recipes

# Verify market_data.json exists
ls -la data/market_data.json
```

### 7. Test the Backend

```bash
# Test uvicorn startup
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, test the API
curl http://localhost:8000/api/admin/console
```

Press `Ctrl+C` to stop the test server.

### 8. Set Up Systemd Service (Production)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/hackathon-backend.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=Hackathon Backend FastAPI
After=network.target

[Service]
Type=notify
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/hackathon/backend
Environment="PATH=/home/YOUR_USERNAME/hackathon/backend/venv/bin"
Environment="OPENAI_API_KEY=your_openai_api_key_here"
ExecStart=/home/YOUR_USERNAME/hackathon/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable hackathon-backend

# Start the service
sudo systemctl start hackathon-backend

# Check status
sudo systemctl status hackathon-backend

# View logs
sudo journalctl -u hackathon-backend -f
```

### 9. Configure Firewall (If Using UFW)

```bash
# Allow SSH (important!)
sudo ufw allow OpenSSH

# Allow HTTP
sudo ufw allow 80

# Allow HTTPS
sudo ufw allow 443

# Allow backend port (if accessing directly)
sudo ufw allow 8000

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 10. Set Up Nginx Reverse Proxy (Optional but Recommended)

```bash
# Install nginx
sudo apt install nginx -y

# Create nginx configuration
sudo nano /etc/nginx/sites-available/hackathon-backend
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your_domain.com;  # Replace with your domain or droplet IP

    client_max_body_size 10M;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Serve frontend static files (if needed)
    location / {
        root /home/YOUR_USERNAME/hackathon/frontend/port_optim/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable the site:

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/hackathon-backend /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 11. Set Up SSL with Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your_domain.com

# Auto-renewal is set up automatically
```

## 🔍 Verification & Testing

```bash
# Check if service is running
sudo systemctl status hackathon-backend

# Test API endpoint
curl http://localhost:8000/api/admin/console

# Test through nginx (if configured)
curl http://YOUR_DROPLET_IP/api/admin/console

# View logs
sudo journalctl -u hackathon-backend -n 100 --no-pager
```

## 🛠 Common Maintenance Commands

```bash
# Restart the backend service
sudo systemctl restart hackathon-backend

# Stop the backend
sudo systemctl stop hackathon-backend

# View live logs
sudo journalctl -u hackathon-backend -f

# Pull latest code
cd ~/hackathon
git pull origin main

# Restart after code update
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart hackathon-backend

# Check disk space
df -h

# Check database sizes
ls -lh data/*.db
```

## 🐛 Troubleshooting

### Service won't start
```bash
# Check detailed logs
sudo journalctl -u hackathon-backend -n 50 --no-pager

# Check if port 8000 is already in use
sudo lsof -i :8000

# Verify Python path
which python3
```

### Database permission errors
```bash
# Fix data directory permissions
cd ~/hackathon/backend
chmod -R 775 data/
```

### Dependencies installation fails
```bash
# Install build dependencies
sudo apt install build-essential python3-dev libssl-dev libffi-dev -y

# Try installing with no cache
pip install --no-cache-dir -r requirements.txt
```

## 📝 Quick Reference

| Action | Command |
|--------|---------|
| View logs | `sudo journalctl -u hackathon-backend -f` |
| Restart service | `sudo systemctl restart hackathon-backend` |
| Check status | `sudo systemctl status hackathon-backend` |
| Update code | `cd ~/hackathon && git pull && sudo systemctl restart hackathon-backend` |
| Access API | `http://YOUR_IP:8000/api/` |

## 🔐 Security Recommendations

1. **Never commit secrets**: Keep API keys in environment variables
2. **Use SSH keys**: Disable password authentication
3. **Keep system updated**: Run `sudo apt update && sudo apt upgrade` regularly
4. **Enable firewall**: Use UFW to restrict access
5. **Use HTTPS**: Set up SSL certificates with Let's Encrypt
6. **Regular backups**: Backup the `data/` directory regularly
7. **Monitor logs**: Set up log monitoring and alerts

## 📊 Performance Tuning

For production workloads, adjust gunicorn workers:

```bash
# Edit systemd service
sudo nano /etc/systemd/system/hackathon-backend.service

# Change workers based on CPU cores (formula: 2 * CPU_CORES + 1)
ExecStart=... -w 4 ...  # Change 4 to your optimal worker count

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart hackathon-backend
```

---

**Ready to deploy!** Start from Step 1 and work your way through. 🚀
