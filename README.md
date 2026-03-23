# EV Charging Station Simulation Platform

Full-stack web platform for EV traffic-flow and charging-station competition simulation.

It combines:
- React frontend (`client/Opt-Frontend`)
- Node.js API backend (`server/server.js`)
- Python simulation engine (`run_simulation.py`, `ev_tc_7.py`, `ev_tc_9_web.py`)

## What This Project Does

1. Runs a simulation from the browser with configurable parameters.
2. Executes Python simulation logic from the Node backend.
3. Returns three result formats:
- Interactive network data (playable timeline)
- Animated network GIF
- Static analytical plots
4. Shows all results in one UI with mode switching.

## Main Features

- Two simulation network types:
- `tc7`: 4-node, 2-station network
- `tc9`: 9-node, 4-station network
- Configurable run parameters from frontend:
- `duration` (seconds)
- `points` (time samples)
- Three result views:
- Interactive network player (timeline + draggable nodes)
- GIF player with playback controls
- Static graphs with next/previous navigation + thumbnails
- Backend health endpoint and simulation endpoint
- CORS-enabled API for hosted deployments
- Production API base-path support (`/api`) for reverse-proxy setups

## Tech Stack

- Frontend: React + Vite
- Backend: Express (Node.js)
- Simulation: Python, NumPy, SciPy, NetworkX, Matplotlib

## Repository Structure

```text
opt/
|-- client/
|   `-- Opt-Frontend/
|       |-- src/
|       |   |-- App.jsx
|       |   |-- GifPlayer.jsx
|       |   `-- InteractiveNetworkPlayer.jsx
|       |-- .env.production
|       `-- package.json
|-- server/
|   |-- server.js
|   `-- package.json
|-- ev_tc_7.py
|-- ev_tc_9_web.py
|-- run_simulation.py
|-- requirements.txt
|-- render.yaml
|-- PREP_IIT_UPLOAD.bat
`-- PREP_IIT_UPLOAD.sh
```

## Prerequisites

- Node.js 18+ (recommended)
- npm
- Python 3.10+ (3.11/3.12 also fine)
- pip

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Local Setup (Step-by-Step)

### 1) Clone and install dependencies

```bash
git clone <your-repo-url>
cd opt

cd server
npm install
cd ..

cd client/Opt-Frontend
npm install
cd ../..

pip install -r requirements.txt
```

### 2) Run backend

```bash
cd server
npm start
```

Backend runs at `http://localhost:3000` by default.

### 3) Run frontend

Open a second terminal:

```bash
cd client/Opt-Frontend
npm run dev
```

Frontend usually runs at `http://localhost:5173`.

### 4) Use the app

1. Choose `TC-7` or `TC-9`.
2. Set `Duration` and `Time Points`.
3. Click `Run Simulation`.
4. Switch between `Interactive`, `Animation`, and `Graphs` views.

## API Behavior and Data Flow

### Endpoint

- `GET /health` -> basic health/version
- `POST /api/run-simulation` -> executes Python simulation

Sample request:

```json
{
  "duration": 70,
  "points": 400,
  "simType": "tc9"
}
```

Response shape (successful):

```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Simulation completed successfully...",
    "graphs": ["base64png..."],
    "animation": "base64gif...",
    "networkData": {
      "nodes": [],
      "edges": [],
      "timePoints": [],
      "densities": [],
      "stationPrices": {},
      "duration": 70
    }
  }
}
```

### Runtime path

1. Frontend sends POST to backend.
2. Node backend spawns `python run_simulation.py <duration> <points> <simType>`.
3. Python collects plots/GIF/data and returns JSON.
4. Frontend renders returned datasets.

## Environment Variables

### Frontend

- `VITE_API_URL`

Current production default is `'/api'`, which is suitable when a reverse proxy maps `/api/*` to backend.

`App.jsx` fallback logic:
- Dev -> `http://localhost:3000`
- Prod -> `/api` if `VITE_API_URL` is unset

### Backend

- `PORT` (default: `3000`)
- `NODE_ENV`
- `CORS_ORIGIN` (default: `*`)

For institute deployment, use `PORT=5100`.

## Deployment Options

## 1) Render Deployment

The repo includes `render.yaml`.

- Backend service: Node runtime
- Frontend service: Static site (Vite build)

Steps:
1. Connect repo in Render.
2. Create Blueprint from `render.yaml`.
3. Set frontend `VITE_API_URL` if needed.
4. Deploy.

## 2) IIT KGP Server Deployment (SFTP/SSH)

This is the flow for your institute-managed environment.

### A) Prepare deployment bundle (on your current PC)

Windows:

```bat
PREP_IIT_UPLOAD.bat
```

Linux/macOS:

```bash
chmod +x PREP_IIT_UPLOAD.sh
./PREP_IIT_UPLOAD.sh
```

This generates:
- `deploy_iit/frontend` (ready static files)
- `deploy_iit/backend` (runtime files + start script)

### B) Upload from whitelisted PC

1. Configure network on that PC with institute-provided IP details.
2. Use WinSCP/FileZilla to connect to `academicweb.iitkgp.ac.in`.
3. Upload:
- `deploy_iit/frontend/*` -> web root directory
- `deploy_iit/backend/*` -> backend runtime directory

### C) Start backend on port 5100

SSH into server and run in backend directory:

Linux shell:

```bash
bash start_backend_5100.sh
```

Windows shell:

```bat
start_backend_5100.bat
```

### D) Reverse proxy requirement

Ask admin team to route `/api/*` to backend service on port `5100`.

### E) Test

1. Health endpoint works.
2. Frontend loads in test URL.
3. Simulation runs for both `tc7` and `tc9`.

## Quick Commands

### Full local run (manual)

```bash
# terminal 1
cd server && npm start

# terminal 2
cd client/Opt-Frontend && npm run dev
```

### Stop Node processes on Windows (if port is stuck)

```powershell
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Troubleshooting

### Frontend says backend not reachable

- Ensure backend is running.
- Confirm API URL used by frontend (`VITE_API_URL` / fallback).
- Check browser network tab for failing URL.

### `Python script failed` from backend

- Verify Python exists in PATH.
- Verify dependencies:

```bash
pip install -r requirements.txt
```

- Run direct test:

```bash
python run_simulation.py 70 400 tc7
python run_simulation.py 70 400 tc9
```

### Port conflict on 3000 or 5100

- Change `PORT` env var, or stop process using that port.

### Graphs empty or animation missing

- Check backend logs for JSON parse or matplotlib errors.
- Reduce `points` temporarily and retry.

## Security Notes

- Never commit credentials/passwords in repo.
- If credentials were shared in screenshots/chat, rotate them.
- Use `.env` files or server secret manager for sensitive values.

## Credits

Developed by Saswat Padhy, Kshitij Mehta, and Aaditya Chari.
