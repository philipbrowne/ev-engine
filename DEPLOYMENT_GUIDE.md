# EV Engine - Deployment Guide

## Overview
This guide covers multiple deployment options for the EV Engine Streamlit application, ranked by cost and complexity.

---

## Option 1: Streamlit Community Cloud (FREE) ⭐ RECOMMENDED

**Cost**: $0/month
**Complexity**: ⭐ (Easiest)
**Best for**: Personal use, quick deployment

### Features
- ✅ Free forever
- ✅ Built-in authentication
- ✅ Auto-deploy from GitHub
- ✅ HTTPS included
- ✅ No server management
- ⚠️ App sleeps after inactivity (wakes on access in ~30 seconds)
- ⚠️ 1 GB RAM limit

### Step-by-Step Setup

#### 1. Prepare Your Repository

```bash
# Make sure your code is committed
git add .
git commit -m "Prepare for deployment"
git push origin main
```

#### 2. Create Streamlit Secrets File

Create `.streamlit/secrets.toml` (don't commit this):

```toml
# .streamlit/secrets.toml
ODDS_API_KEY = "your_api_key_here"

# Authentication
[passwords]
admin = "your_secure_password_here"  # Change this!
```

Add to `.gitignore`:
```
.streamlit/secrets.toml
```

#### 3. Add Authentication to dashboard.py

Add this at the very top of `dashboard.py`:

```python
import streamlit as st
import hmac

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["passwords"]["admin"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

# Rest of your dashboard code continues here...
```

#### 4. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set main file: `dashboard.py`
6. Click "Advanced settings"
7. Paste your secrets from `.streamlit/secrets.toml`
8. Click "Deploy"

#### 5. Your App is Live!

- URL: `https://your-app-name.streamlit.app`
- Share only with people you trust
- They'll need the password to access

### Keeping App Awake

The app sleeps after inactivity. To keep it warm:

**Option A: Ping Service (Free)**
Use UptimeRobot or similar to ping your app every 5 minutes:
- Sign up at [uptimerobot.com](https://uptimerobot.com) (free)
- Create HTTP monitor for your Streamlit URL
- Check interval: 5 minutes

**Option B: Cron Job (Free)**
```bash
# Add to your local crontab (runs every 5 minutes)
*/5 * * * * curl -s https://your-app.streamlit.app > /dev/null
```

---

## Option 2: Railway (FREE Tier) 💰

**Cost**: $0/month (500 hours free) then ~$5/month
**Complexity**: ⭐⭐ (Easy)
**Best for**: Always-on deployment with database

### Features
- ✅ 500 hours/month free (enough for 24/7 with one app)
- ✅ Persistent storage
- ✅ No sleep mode
- ✅ PostgreSQL option (for scaling)
- ⚠️ Requires credit card for free tier
- ⚠️ $5/month after free hours

### Setup

1. **Prepare for Railway**

Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Create `Procfile`:
```
web: streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0
```

2. **Add HTTP Basic Auth**

Create `streamlit_app.py` wrapper:
```python
import os
import streamlit as st

# Simple password check
def check_password():
    password = st.text_input("Enter password:", type="password")
    if password == os.environ.get("APP_PASSWORD", ""):
        return True
    elif password:
        st.error("Incorrect password")
    return False

if check_password():
    # Import and run main dashboard
    import dashboard
else:
    st.stop()
```

3. **Deploy**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize
railway init

# Add environment variables
railway variables set ODDS_API_KEY=your_key
railway variables set APP_PASSWORD=your_secure_password

# Deploy
railway up
```

---

## Option 3: Render (FREE Tier) 💰

**Cost**: $0/month for web service (spins down after inactivity)
**Complexity**: ⭐⭐ (Easy)
**Best for**: Cost-conscious, okay with cold starts

### Features
- ✅ Completely free
- ✅ Auto-deploy from GitHub
- ✅ HTTPS included
- ⚠️ Spins down after 15 min inactivity
- ⚠️ ~30 second cold start

### Setup

1. Create `render.yaml`:
```yaml
services:
  - type: web
    name: ev-engine
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: ODDS_API_KEY
        sync: false
      - key: APP_PASSWORD
        sync: false
```

2. Deploy at [render.com](https://render.com)
   - Connect GitHub repo
   - Set environment variables
   - Deploy

---

## Option 4: Oracle Cloud Always Free Tier (FREE) 🔧

**Cost**: $0/month forever
**Complexity**: ⭐⭐⭐⭐ (Advanced)
**Best for**: Technical users, full control

### Features
- ✅ Actually free forever (not a trial)
- ✅ 2 VM instances (1 GB RAM each)
- ✅ 200 GB storage
- ✅ Always on, no sleep
- ✅ Full root access
- ⚠️ Requires manual server setup
- ⚠️ You manage everything

### Resources Included FREE Forever
- 2x VM.Standard.E2.1.Micro instances (1 GB RAM, 1 OCPU each)
- 200 GB block storage
- 10 TB outbound data transfer/month

### Quick Setup

1. **Create Oracle Cloud Account**
   - Go to [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)
   - Sign up (requires credit card but won't charge for Always Free)

2. **Create VM Instance**
   - Choose Ubuntu 22.04
   - Select Always Free shape: VM.Standard.E2.1.Micro
   - Save SSH keys

3. **SSH and Setup**
```bash
ssh ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv nginx -y

# Clone your repo
git clone https://github.com/yourusername/ev-engine.git
cd ev-engine

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
nano .env
# Add: ODDS_API_KEY=your_key

# Install and configure Nginx for password protection
sudo apt install apache2-utils -y
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/ev-engine
```

Nginx config:
```nginx
server {
    listen 80;
    server_name your-ip-or-domain;

    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ev-engine /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Create systemd service for Streamlit
sudo nano /etc/systemd/system/ev-engine.service
```

Systemd service:
```ini
[Unit]
Description=EV Engine Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ev-engine
Environment="PATH=/home/ubuntu/ev-engine/venv/bin"
ExecStart=/home/ubuntu/ev-engine/venv/bin/streamlit run dashboard.py --server.port 8501 --server.address localhost
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl daemon-reload
sudo systemctl enable ev-engine
sudo systemctl start ev-engine

# Check status
sudo systemctl status ev-engine
```

4. **Configure Firewall**
```bash
# Oracle Cloud has both OS firewall and cloud firewall
# OS firewall
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# Also add ingress rule in Oracle Cloud Console:
# Networking → Virtual Cloud Networks → Your VCN → Security Lists
# Add Ingress Rule: 0.0.0.0/0, TCP, port 80
```

5. **Optional: Setup SSL with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Option 5: AWS EC2 Free Tier (FREE for 12 months) ⏰

**Cost**: Free for 12 months, then ~$8/month
**Complexity**: ⭐⭐⭐⭐ (Advanced)
**Best for**: AWS users, temporary free hosting

### Features
- ✅ 750 hours/month free (t2.micro) for 12 months
- ✅ Full control
- ⚠️ Free tier expires after 12 months
- ⚠️ Complex setup
- ⚠️ Can accidentally incur charges

Setup similar to Oracle Cloud but using AWS EC2 t2.micro instance.

---

## Cost Comparison

| Option | Monthly Cost | Setup Time | Always On | Auth |
|--------|-------------|------------|-----------|------|
| **Streamlit Cloud** | $0 | 15 min | No* | ✅ |
| **Railway** | $0-5 | 20 min | Yes | ✅ |
| **Render** | $0 | 20 min | No* | ✅ |
| **Oracle Cloud** | $0 | 2 hours | Yes | ✅ |
| **AWS EC2** | $0-8 | 2 hours | Yes | ✅ |

*Can be kept awake with ping service

---

## Authentication Methods Summary

### 1. Streamlit Built-in (Recommended)
```python
# Uses st.secrets and password check
if not check_password():
    st.stop()
```

### 2. HTTP Basic Auth (Nginx)
```nginx
auth_basic "Restricted";
auth_basic_user_file /etc/nginx/.htpasswd;
```

### 3. Streamlit-Authenticator Library
```bash
pip install streamlit-authenticator
```

```python
import streamlit_authenticator as stauth

authenticator = stauth.Authenticate(
    credentials,
    'ev_engine_cookie',
    'signature_key',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Login', 'main')
```

---

## My Recommendation: Streamlit Cloud + UptimeRobot

**Total Cost**: $0/month
**Setup Time**: 15 minutes
**Maintenance**: None

**Why?**
1. Completely free
2. Easiest setup (no server management)
3. Built-in auth
4. HTTPS included
5. UptimeRobot keeps it warm
6. Auto-deploys from Git

**When to upgrade?**
- If you need always-on without pinging → Oracle Cloud Free Tier
- If you need more resources → Railway ($5/month)
- If you want PostgreSQL → Railway or Oracle Cloud

---

## Quick Start: Deploy to Streamlit Cloud Now

```bash
# 1. Add authentication to dashboard.py (see code above)
# 2. Create .streamlit/secrets.toml with your secrets
# 3. Add secrets.toml to .gitignore
# 4. Push to GitHub
git add .
git commit -m "Add authentication"
git push

# 5. Go to share.streamlit.io and deploy
# 6. Add secrets in Streamlit Cloud dashboard
# 7. Done! Share your URL with password
```

Your app will be live at: `https://[your-app-name].streamlit.app`

---

## Security Best Practices

1. **Strong Password**: Use a password manager to generate a strong password
2. **Environment Variables**: Never commit secrets to Git
3. **HTTPS Only**: All options above include HTTPS
4. **Regular Updates**: Keep dependencies updated
5. **Monitor Logs**: Check for unauthorized access attempts
6. **API Key Rotation**: Rotate your Odds API key periodically
7. **Rate Limiting**: Monitor your API usage in the app

---

## Troubleshooting

### App won't start
- Check logs in platform dashboard
- Verify all environment variables are set
- Check Python version compatibility

### Authentication not working
- Verify secrets are properly set
- Check for typos in password
- Clear browser cache/cookies

### Database issues
- SQLite works fine for single user
- For multiple users, migrate to PostgreSQL (Railway offers free tier)

### API quota exhausted
- Check that only you have access (authentication working)
- Monitor usage in The Odds API dashboard
- Adjust refresh frequency if needed

---

## Next Steps

1. Choose your deployment option (Streamlit Cloud recommended)
2. Follow the setup guide
3. Test authentication
4. Set up monitoring (UptimeRobot for Streamlit Cloud)
5. Enjoy your deployed EV Engine! 🚀
