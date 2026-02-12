# EV Charging Station Simulation - Deployment Guide

## Architecture Overview

This project consists of:
1. **Frontend** (React/Vite) - Static Site
2. **Backend** (Node.js + Python) - Web Service

Both are deployed to **Render.com** for simplicity - one dashboard, easy custom domains, free tier available.

---

## Deploy to Render.com (Recommended)

### Prerequisites

- GitHub account with your code pushed
- [Render.com](https://render.com) account (free)

### Step 1: Deploy Backend (Web Service)

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `ev-simulation-api`
   - **Root Directory**: `server`
   - **Runtime**: `Node`
   - **Build Command**: `npm install && cd .. && pip install -r requirements.txt`
   - **Start Command**: `node server.js`
5. Select **Free** plan
6. Click **"Create Web Service"**

Wait for deployment to complete. Copy your backend URL:
```
https://ev-simulation-api.onrender.com
```

### Step 2: Deploy Frontend (Static Site)

1. Click **"New +"** → **"Static Site"**
2. Connect the same GitHub repository
3. Configure the site:
   - **Name**: `ev-simulation`
   - **Root Directory**: `client/Opt-Frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add **Environment Variable**:
   - Key: `VITE_API_URL`
   - Value: `https://ev-simulation-api.onrender.com` (your backend URL from Step 1)
5. Click **"Create Static Site"**

Your frontend will be available at:
```
https://ev-simulation.onrender.com
```

---

## Custom Domain Setup (Easy!)

Render makes custom domains super simple:

### Add Custom Domain

1. Go to your service in Render dashboard
2. Click **Settings** → **Custom Domains**
3. Click **"Add Custom Domain"**
4. Enter your domain: `yourdomain.com`

### Configure DNS

Render will show you exactly what DNS record to add:

| Type | Name | Value |
|------|------|-------|
| CNAME | `www` | `ev-simulation.onrender.com` |
| CNAME | `api` | `ev-simulation-api.onrender.com` |

Or for apex domain (@):
| Type | Name | Value |
|------|------|-------|
| A | `@` | Render's IP (shown in dashboard) |

### SSL Certificate

- **Automatic and free!**
- Render provisions SSL within minutes after DNS propagation
- No configuration needed

---

## Using render.yaml (Auto-Deploy)

The project includes a `render.yaml` file for Blueprint deployments:

1. Go to Render Dashboard → **Blueprints**
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repo
4. Render reads `render.yaml` and creates both services automatically
5. **Important**: After first deploy, set `VITE_API_URL` in the frontend service to your backend URL

---

## Local Development

### Run Backend
```bash
cd server
npm install
node server.js
```

### Run Frontend
```bash
cd client/Opt-Frontend
npm install
npm run dev
```

The frontend uses `http://localhost:3000` for API calls in development.

---

## Troubleshooting

### 405 Error (Method Not Allowed)
Frontend is calling the wrong backend URL:

1. **Check Environment Variable** in Render:
   - Go to your Static Site → Environment
   - Verify `VITE_API_URL` = `https://your-backend.onrender.com`
   - Must include `https://`

2. **Redeploy after changing env vars**:
   - Click **"Manual Deploy"** → **"Deploy latest commit"**

3. **Test backend directly**:
   ```bash
   # Should return {"status":"ok",...}
   curl https://ev-simulation-api.onrender.com/health
   
   # Run simulation
   curl -X POST https://ev-simulation-api.onrender.com/api/run-simulation
   ```

### Cold Start Delay (Free Tier)
Free tier services sleep after 15 minutes of inactivity:
- First request may take 30-60 seconds
- Subsequent requests are fast
- Upgrade to paid plan to avoid this

### CORS Issues
The backend includes CORS middleware. If issues persist:
- Check Render logs for errors
- Verify frontend URL in browser devtools Network tab

### Python Dependencies
Ensure `requirements.txt` is in project root:
```
numpy
matplotlib
networkx
scipy
imageio
```

---

## Project URLs (Update after deployment)

- **Frontend**: https://ev-simulation.onrender.com
- **Backend**: https://ev-simulation-api.onrender.com
- **API Endpoint**: https://ev-simulation-api.onrender.com/api/run-simulation

### With Custom Domain (example)
- **Frontend**: https://yourdomain.com
- **Backend**: https://api.yourdomain.com
