# Frontend Deployment Guide - Digital Ocean VM

Deploy the React frontend to the same Digital Ocean droplet as the backend.

## 📋 Architecture

- **Frontend**: Static files served by nginx
- **Backend**: Python FastAPI on port 8000
- **Nginx**: Reverse proxy + static file server
  - Serves frontend from `/var/www/hackathon`
  - Proxies `/api/*` → `http://localhost:8000/*`

---

## 🚀 Step-by-Step Deployment

### 1. Build the Frontend Locally (Windows)

```powershell
# Navigate to frontend directory
cd C:\Python\hackathon\frontend\port_optim

# Install dependencies (if not already done)
npm install

# Build for production (uses .env.production)
npm run build
```

This creates a `dist/` folder with optimized static files.

### 2. Upload Built Files to Droplet

```powershell
# Create target directory on droplet
ssh root@167.172.198.36 "mkdir -p /var/www/hackathon"

# Upload the built files
scp -r dist/* root@167.172.198.36:/var/www/hackathon/
```

**Alternative (using rsync for faster incremental updates):**
```powershell
# If you have WSL or Git Bash with rsync
rsync -avz --delete dist/ root@167.172.198.36:/var/www/hackathon/
```

### 3. Install and Configure Nginx on Droplet

SSH into your droplet and run:

```bash
# Install nginx
sudo apt update
sudo apt install nginx -y

# Create nginx configuration
sudo nano /etc/nginx/sites-available/hackathon
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name 167.172.198.36;  # Replace with your domain if you have one

    root /var/www/hackathon;
    index index.html;

    # Frontend static files
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, must-revalidate";
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable the site:**

```bash
# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/hackathon /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx to start on boot
sudo systemctl enable nginx
```

### 4. Update Firewall (if needed)

```bash
# Allow HTTP traffic
sudo ufw allow 80

# Allow HTTPS (for future SSL setup)
sudo ufw allow 443

# Check firewall status
sudo ufw status
```

### 5. Verify Deployment

**Test the backend API:**
```bash
curl http://localhost:8000/admin/console
```

**Test nginx proxy:**
```bash
curl http://localhost/api/admin/console
```

**Test from your browser:**
```
http://167.172.198.36
```

You should see your frontend application! 🎉

---

## 🔄 Update Workflow (After Code Changes)

### Quick Update (Frontend Only)

```powershell
# On Windows
cd C:\Python\hackathon\frontend\port_optim
npm run build
scp -r dist/* root@167.172.198.36:/var/www/hackathon/
```

No nginx restart needed for static file updates.

### Backend Update

```bash
# On droplet
cd ~/hackathon
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Restart backend
# If running manually: Ctrl+C and restart uvicorn
# If using systemd:
sudo systemctl restart hackathon-backend
```

---

## 🔐 SSL Setup (Optional but Recommended)

### Using Let's Encrypt (Free SSL)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Certbot will automatically update nginx config and set up auto-renewal
```

**If using IP address only:**
SSL requires a domain name. Consider getting a free domain from:
- Freenom.com
- No-IP.com
- Or use Digital Ocean's DNS

---

## 🛠 Troubleshooting

### Frontend shows blank page

```bash
# Check nginx error logs
sudo tail -f /var/nginx/error.log

# Check if files exist
ls -la /var/www/hackathon/

# Verify nginx is running
sudo systemctl status nginx
```

### API calls fail (CORS errors)

Check backend CORS settings in `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 502 Bad Gateway

Backend is not running:

```bash
# Check backend status
sudo systemctl status hackathon-backend

# Or if running manually
ps aux | grep uvicorn

# Restart backend
sudo systemctl restart hackathon-backend
```

### File permissions

```bash
# Fix permissions on frontend files
sudo chown -R www-data:www-data /var/www/hackathon/
sudo chmod -R 755 /var/www/hackathon/
```

---

## 📊 Performance Tips

### Enable Gzip Compression

Add to nginx config inside `server` block:

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
```

### Cache Static Assets

Already configured in the nginx config above with:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## 🔍 Monitoring

### View nginx access logs
```bash
sudo tail -f /var/log/nginx/access.log
```

### View nginx error logs
```bash
sudo tail -f /var/log/nginx/error.log
```

### View backend logs
```bash
# If using systemd
sudo journalctl -u hackathon-backend -f

# If running manually
# Logs appear in terminal where uvicorn is running
```

---

## 📝 Quick Reference

| What | Command |
|------|---------|
| Rebuild frontend | `cd frontend/port_optim && npm run build` |
| Upload frontend | `scp -r dist/* root@167.172.198.36:/var/www/hackathon/` |
| Restart nginx | `sudo systemctl restart nginx` |
| Test nginx config | `sudo nginx -t` |
| View nginx logs | `sudo tail -f /var/log/nginx/error.log` |
| Access URL | `http://167.172.198.36` |
| API endpoint | `http://167.172.198.36/api/admin/console` |

---

**Your app is now fully deployed!** Frontend and backend running on the same VM. 🚀
