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

## Step 3: Alternative Backend - Render.com

If you prefer Render over Railway:

### 3.1 Create render.yaml

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

### 3.2 Deploy

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

### CORS Issues
The backend already includes CORS middleware. If you face issues:
- Ensure the frontend URL is correct
- Check Railway/Render logs for errors

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
