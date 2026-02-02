# Quick Deploy Guide - EV Engine

## ✅ Authentication Setup Complete!

I've already added authentication to your dashboard. Here's what was done:

### Changes Made:
1. ✅ Created `auth.py` - Authentication module
2. ✅ Added authentication check to `dashboard.py` (top of file)
3. ✅ Added logout button to sidebar
4. ✅ Created `.streamlit/secrets.toml.example` template
5. ✅ Updated `.gitignore` to exclude secrets

---

## 🚀 Test Locally First (5 minutes)

### Step 1: Create Your Secrets File

```bash
# Copy the example file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

### Step 2: Edit Your Secrets

Open `.streamlit/secrets.toml` and add your actual values:

```toml
# Your actual Odds API key
ODDS_API_KEY = "your_real_api_key_here"

# Choose a strong password!
[passwords]
admin = "YourSecurePassword123!"
```

**Important**: Use a strong password! This protects your API quota.

### Step 3: Test Authentication

```bash
# Run the dashboard
streamlit run dashboard.py
```

You should see:
1. 🔐 A login screen
2. Enter your password
3. Dashboard loads after successful login
4. 🚪 Logout button in sidebar

**Test it works**: Try entering wrong password first, then correct one.

---

## 🌐 Deploy to Streamlit Cloud (10 minutes)

### Step 1: Commit Your Code (DON'T commit secrets!)

```bash
# Check what's being committed (secrets.toml should NOT appear)
git status

# You should see:
# - auth.py (new)
# - dashboard.py (modified)
# - .streamlit/secrets.toml.example (new)
# - .gitignore (modified)
#
# You should NOT see:
# - .streamlit/secrets.toml (this is secret!)

# Commit the changes
git add .
git commit -m "Add authentication for secure deployment"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud

1. **Go to**: [share.streamlit.io](https://share.streamlit.io)

2. **Sign in** with GitHub

3. **Click**: "New app"

4. **Configure**:
   - Repository: Select your `ev-engine` repo
   - Branch: `main`
   - Main file path: `dashboard.py`

5. **Click**: "Advanced settings..."

6. **Paste your secrets** (copy from `.streamlit/secrets.toml`):
   ```toml
   ODDS_API_KEY = "your_real_api_key_here"

   [passwords]
   admin = "YourSecurePassword123!"
   ```

7. **Click**: "Deploy!"

### Step 3: Wait for Deployment (~2 minutes)

You'll see:
- Installing dependencies...
- Starting app...
- ✅ Your app is live!

### Step 4: Test Your Deployed App

1. Click the URL (e.g., `https://your-app-name.streamlit.app`)
2. You should see the login screen
3. Enter your password
4. Dashboard loads!

🎉 **You're live!**

---

## 🔐 Security Checklist

✅ Password configured in secrets
✅ Secrets file NOT committed to Git
✅ HTTPS enabled (automatic)
✅ Only you have the password
✅ Logout button available

---

## 📱 Access Your App

**Your URL**: `https://[your-app-name].streamlit.app`

**Share with others**: Give them the URL + password (only people you trust!)

**Access from anywhere**: Phone, tablet, laptop - works on all devices

---

## 🔄 Keep App Awake (Optional)

Your app sleeps after 15 minutes of inactivity. To keep it always-on:

### Option A: UptimeRobot (Recommended - FREE)

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up (free account)
3. Click "Add New Monitor"
4. Settings:
   - Monitor Type: HTTP(s)
   - Friendly Name: EV Engine
   - URL: `https://your-app-name.streamlit.app`
   - Monitoring Interval: 5 minutes
5. Click "Create Monitor"

Done! App stays awake 24/7 for free.

### Option B: Local Cron Job (if you have a computer always on)

**Mac/Linux**:
```bash
# Edit crontab
crontab -e

# Add this line (pings every 5 minutes):
*/5 * * * * curl -s https://your-app-name.streamlit.app > /dev/null
```

**Windows** (Task Scheduler):
Create a task that runs every 5 minutes:
```powershell
Invoke-WebRequest -Uri https://your-app-name.streamlit.app
```

---

## 🔧 Troubleshooting

### "Module not found" error
- Check that `auth.py` is committed and pushed
- Redeploy the app

### "Secrets not found" error
- Make sure you pasted secrets in "Advanced settings"
- Check formatting (TOML format is picky about quotes)

### Password not working
- Check for typos in password
- Password is case-sensitive
- Try clearing browser cache/cookies

### App very slow
- First load after sleep takes ~30 seconds (normal)
- Set up UptimeRobot to keep it awake

### Can't find my app URL
- Go to share.streamlit.io
- Click on your app name
- URL is shown at the top

---

## 📊 Monitor Your API Usage

Check your API quota in the dashboard:
1. Log in to your app
2. Look at the metrics at the top
3. Track "Active Slips" to monitor activity

Also check The Odds API dashboard:
- [https://the-odds-api.com/account/](https://the-odds-api.com/account/)
- See remaining requests
- View usage history

---

## 🔄 Update Your App

Any changes you push to GitHub automatically deploy:

```bash
# Make changes to your code
git add .
git commit -m "Update: improved analytics"
git push

# Streamlit Cloud automatically redeploys!
# Wait ~2 minutes for new version to be live
```

---

## 💡 Pro Tips

1. **Bookmark your app URL** for quick access
2. **Save password in password manager** (don't lose it!)
3. **Check API quota weekly** to avoid surprises
4. **Use UptimeRobot** to keep app always-on
5. **Only share with trusted people** (protects your quota)

---

## 🎯 Success Checklist

Before you close this guide, verify:

- [ ] Tested authentication locally (works!)
- [ ] App deployed to Streamlit Cloud
- [ ] Can access app with password
- [ ] Logout button works
- [ ] Secrets NOT committed to Git
- [ ] URL bookmarked
- [ ] Password saved in password manager
- [ ] (Optional) UptimeRobot configured

---

## 🆘 Need Help?

**Deployment Issues**:
- Check [Streamlit Community Forum](https://discuss.streamlit.io)
- Review logs in Streamlit Cloud dashboard

**App Issues**:
- Check `ev_engine.log` for errors
- Verify database exists in `data/` directory

**API Issues**:
- Check The Odds API dashboard
- Verify API key is correct in secrets

---

## 🎊 Congratulations!

You now have a **secure, free, cloud-hosted sports betting EV calculator**!

- ✅ Protected with authentication
- ✅ Accessible from anywhere
- ✅ Zero hosting costs
- ✅ Auto-updates from Git
- ✅ Enterprise-grade security

**Total cost: $0/month**

Enjoy finding those +EV opportunities! 🚀📈
