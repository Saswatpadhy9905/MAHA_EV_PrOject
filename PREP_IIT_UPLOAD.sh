#!/bin/bash
set -e

echo ""
echo "========================================"
echo "Prepare IIT Upload Bundle"
echo "========================================"
echo ""

read -r -p "Enter production API URL [default: /api]: " API_URL
API_URL=${API_URL:-/api}

echo "[*] Building frontend with VITE_API_URL=${API_URL}"
cd client/Opt-Frontend
npm install
VITE_API_URL="${API_URL}" npm run build
cd ../..

echo "[*] Creating deploy_iit bundle..."
rm -rf deploy_iit
mkdir -p deploy_iit/frontend deploy_iit/backend

echo "[*] Copying frontend build..."
cp -r client/Opt-Frontend/dist/* deploy_iit/frontend/

echo "[*] Copying backend runtime files..."
cp server/server.js deploy_iit/backend/
cp server/package.json deploy_iit/backend/
if [ -f server/package-lock.json ]; then
  cp server/package-lock.json deploy_iit/backend/
fi
cp requirements.txt deploy_iit/backend/
cp run_simulation.py deploy_iit/backend/
cp ev_tc_*.py deploy_iit/backend/

echo "[*] Writing backend start helper..."
cat > deploy_iit/backend/start_backend_5100.sh <<'EOF'
#!/bin/bash
set -e
npm install
python3 -m pip install -r requirements.txt
export PORT=5100
export NODE_ENV=production
node server.js
EOF
chmod +x deploy_iit/backend/start_backend_5100.sh

echo ""
echo "[OK] Bundle ready at: deploy_iit/"
echo "Upload deploy_iit/frontend to your web root and deploy_iit/backend to server runtime folder."
echo ""
