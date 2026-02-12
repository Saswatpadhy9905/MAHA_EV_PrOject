const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Build version for cache busting
const BUILD_VERSION = '3.2.0-noaim';

// CORS configuration - handle preflight properly for Koyeb/cloud platforms
const corsOptions = {
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With'],
  credentials: true,
  optionsSuccessStatus: 200  // Some legacy browsers choke on 204
};

// Apply CORS middleware
app.use(cors(corsOptions));

// Explicitly handle OPTIONS preflight for all routes
app.options('*', cors(corsOptions));

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', version: BUILD_VERSION, timestamp: new Date().toISOString() });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({ 
    message: 'EV Charging Station Simulation API',
    version: BUILD_VERSION,
    endpoints: {
      health: '/health',
      simulation: '/api/run-simulation (POST)'
    }
  });
});

// Also respond to GET on /api/run-simulation with instructions (prevents 405 on wrong method)
app.get('/api/run-simulation', (req, res) => {
  res.json({ 
    message: 'This endpoint requires a POST request to run the simulation',
    method: 'POST',
    endpoint: '/api/run-simulation'
  });
});

// Run Python code endpoint
app.post('/api/run-simulation', (req, res) => {
  const pythonScriptPath = path.join(__dirname, '..', 'run_simulation.py');
  
  console.log(`[Server] Starting simulation from: ${pythonScriptPath}`);
  console.log(`[Server] Working directory: ${path.join(__dirname, '..')}`);
  
  // Determine Python executable - check various venv locations for cloud platforms
  const isProduction = process.env.NODE_ENV === 'production';
  let pythonCmd = 'python';
  
  if (isProduction) {
    const fs = require('fs');
    // Check multiple possible Python locations
    const pythonPaths = [
      '/opt/render/project/src/.venv/bin/python',
      '/app/venv/bin/python',
      '/usr/bin/python3',
      'python3',
      'python'
    ];
    
    for (const p of pythonPaths) {
      if (p.startsWith('/')) {
        if (fs.existsSync(p)) {
          pythonCmd = p;
          break;
        }
      } else {
        pythonCmd = p;
        break;
      }
    }
  }
  
  console.log(`[Server] Using Python: ${pythonCmd}`);
  
  // Spawn Python process
  const pythonProcess = spawn(pythonCmd, [pythonScriptPath], {
    cwd: path.join(__dirname, '..'),  // Set working directory to project root
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });
  
  let dataOutput = '';
  let errorOutput = '';
  
  // Collect stdout
  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString();
    console.log(`[Python stdout] ${output}`);
    dataOutput += output;
  });
  
  // Collect stderr
  pythonProcess.stderr.on('data', (data) => {
    const error = data.toString();
    console.error(`[Python stderr] ${error}`);
    errorOutput += error;
  });
  
  // Handle process completion
  pythonProcess.on('close', (code) => {
    console.log(`[Server] Python process exited with code ${code}`);
    
    if (code === 0) {
      try {
        // Parse the output assuming the Python script outputs JSON
        const result = JSON.parse(dataOutput);
        console.log(`[Server] Successfully parsed JSON. Graphs: ${result.graphs ? result.graphs.length : 0}`);
        res.json({ success: true, data: result });
      } catch (e) {
        console.error(`[Server] JSON parse error: ${e.message}`);
        console.log(`[Server] Raw output: ${dataOutput.substring(0, 200)}`);
        res.status(500).json({ 
          success: false, 
          error: 'Failed to parse simulation output',
          details: e.message
        });
      }
    } else {
      console.error(`[Server] Python script failed with code ${code}`);
      res.status(500).json({ 
        success: false, 
        error: `Python script failed with code ${code}`,
        details: errorOutput 
      });
    }
  });
  
  // Handle process errors
  pythonProcess.on('error', (err) => {
    console.error(`[Server] Process error: ${err.message}`);
    res.status(500).json({ 
      success: false, 
      error: 'Failed to execute Python script',
      details: err.message 
    });
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});
