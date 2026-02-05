# EV Charging Station Simulation - Deployment Guide

## Architecture Overview

This project consists of:
1. **Frontend** (React/Vite) → Deploy to **Vercel**
2. **Backend** (Node.js + Python) → Deploy to **Railway** or **Render**

The simulation requires Python with heavy dependencies and takes 10-30 seconds to run, 
which exceeds Vercel's serverless function limits. That's why we use a separate backend service.

---

## Step 1: Deploy Backend to Railway (Recommended)

### 1.1 Prepare the Backend

The backend folder already includes everything needed. Make sure you have:
- `server/server.js` - Express server
- `server/package.json` - Node.js dependencies
- `run_simulation.py` - Python simulation script
- `ev_tc_6.py` - Main simulation logic
- `requirements.txt` - Python dependencies

### 1.2 Create Railway Account & Deploy

1. Go to [railway.app](https://railway.app) and sign up
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Connect your GitHub and select your repository
4. Railway will auto-detect the project

### 1.3 Configure Railway

In the Railway dashboard:

1. **Set Root Directory**: Click on your service → Settings → Root Directory → `/server`

2. **Add Build Command**: 
   ```
   npm install && pip install -r ../requirements.txt
   ```

3. **Add Start Command**:
   ```
   node server.js
   ```

4. **Set Environment Variables**:
   - `PORT` = `3000` (Railway provides this automatically)

5. **Generate Domain**: Settings → Networking → Generate Domain
   - Copy the URL (e.g., `https://your-app.railway.app`)

### Alternative: Create a railway.json

Add this file to your project root:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd server && node server.js",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Update Environment Variable

Edit `client/Opt-Frontend/.env.production`:
```
VITE_API_URL=https://your-backend.railway.app
```
Replace with your actual Railway URL from Step 1.

### 2.2 Deploy to Vercel

1. Go to [vercel.com](https://vercel.com) and sign up
2. Click **"Add New Project"** → **"Import Git Repository"**
3. Select your repository
4. Configure the project:
   - **Framework Preset**: Vite
   - **Root Directory**: `client/Opt-Frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add Environment Variable:
   - `VITE_API_URL` = `https://your-backend.railway.app`
6. Click **Deploy**

---

## Step 3: Alternative Backend - Koyeb

If you prefer Koyeb (free tier available):

### 3.1 Deploy to Koyeb

1. Go to [koyeb.com](https://koyeb.com) and sign up
2. Click **"Create App"** → **"GitHub"**
3. Connect your GitHub and select your repository
4. Configure the deployment:
   - **Builder**: Dockerfile
   - **Dockerfile Path**: `Dockerfile` (at root)
   - **Port**: `3000`
   - **Region**: Choose nearest

### 3.2 Environment Variables

Add these in the Koyeb dashboard:
- `PORT` = `3000`
- `NODE_ENV` = `production`
- `KOYEB_SERVICE_NAME` = `opt-backend`

### 3.3 Health Check Configuration

Configure in Koyeb dashboard:
- **Path**: `/health`
- **Port**: `3000`
- **Interval**: 30 seconds

### 3.4 Get Your URL

After deployment:
1. Go to your app's overview in Koyeb
2. Copy the URL (e.g., `https://opt-backend-yourname.koyeb.app`)
3. **Update the frontend** `.env.production` file:
   ```
   VITE_API_URL=https://opt-backend-yourname.koyeb.app
   ```
4. **Also set in Vercel dashboard** → Environment Variables:
   - `VITE_API_URL` = `https://opt-backend-yourname.koyeb.app`
5. **Redeploy your Vercel frontend** after updating the environment variable

### 3.5 Verify Koyeb Deployment

Test your backend directly:
```bash
# Check health
curl https://opt-backend-yourname.koyeb.app/health

# Test API (should return method info, not 405)
curl https://opt-backend-yourname.koyeb.app/api/run-simulation

# Run simulation
curl -X POST https://opt-backend-yourname.koyeb.app/api/run-simulation
```

---

## Step 4: Alternative Backend - Render.com

If you prefer Render:

### 4.1 Create render.yaml

Add to project root:
```yaml
services:
  - type: web
    name: ev-simulation-api
    env: node
    buildCommand: npm install && pip install -r requirements.txt
    startCommand: node server/server.js
    envVars:
      - key: NODE_ENV
        value: production
```

### 4.2 Deploy

1. Go to [render.com](https://render.com) and sign up
2. New → Web Service → Connect GitHub
3. Render auto-detects `render.yaml`
4. Copy the URL and update Vercel environment variable

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

The frontend will use `http://localhost:3000` for API calls in development.

---

## Troubleshooting

### 405 Error (Method Not Allowed)
This usually means the frontend is calling the wrong backend URL:

1. **Check your Vercel Environment Variable**:
   - Go to Vercel dashboard → Your Project → Settings → Environment Variables
   - Verify `VITE_API_URL` is set to your **actual Koyeb/Railway URL**
   - Must include `https://` prefix
   
2. **Redeploy after changing env vars**:
   - Vercel doesn't auto-redeploy when you change env vars
   - Click **Redeploy** after updating `VITE_API_URL`

3. **Test your backend directly**:
   ```bash
   # Should return {"status":"ok",...}
   curl https://your-backend.koyeb.app/health
   
   # Should return JSON, not 405
   curl -X POST https://your-backend.koyeb.app/api/run-simulation
   ```

4. **Check browser console**:
   - Open browser DevTools (F12)
   - Look at Network tab to see which URL is being called
   - If it shows `localhost:3000`, the env var isn't set correctly

### CORS Issues
The backend already includes CORS middleware. If you face issues:
- Ensure the frontend URL is correct
- Check Railway/Render/Koyeb logs for errors

### Python Dependencies
Make sure `requirements.txt` is in the project root with:
```
numpy
matplotlib
networkx
scipy
imageio
```

### Timeout Issues
Railway has a 5-minute timeout. If simulations fail:
- Reduce simulation complexity in `ev_tc_6.py`
- Consider caching results for common configurations

---

## Project URLs (Update after deployment)

- **Frontend (Vercel)**: https://your-app.vercel.app
- **Backend (Railway)**: https://your-backend.railway.app
- **API Endpoint**: https://your-backend.railway.app/api/run-simulation
