# EV Charging Station Simulation - Web Application

A full-stack web application that runs a Python-based EV charging station competition simulation and displays the results as interactive graphs.

## Project Structure

```
opt/
├── ev_tc_1.py              # Main Python simulation code
├── run_simulation.py        # Wrapper to run simulation and output graphs
├── client/
│   └── Opt-Frontend/       # React frontend
│       ├── src/
│       │   ├── App.jsx     # Main React component
│       │   ├── App.css     # Styling
│       │   ├── main.jsx
│       │   └── index.css
│       ├── package.json
│       ├── vite.config.js
│       └── index.html
└── server/
    ├── server.js           # Express backend
    └── package.json
```

## Prerequisites

- **Node.js** (v14 or higher)
- **Python** (v3.8 or higher)
- Python packages: `networkx`, `numpy`, `matplotlib`, `scipy`

## Installation

### Backend Setup

1. Navigate to the server directory:
```bash
cd server
```

2. Install Node dependencies:
```bash
npm install
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd client/Opt-Frontend
```

2. Install Node dependencies:
```bash
npm install
```

### Python Dependencies

Install required Python packages:
```bash
pip install networkx numpy matplotlib scipy
```

## Running the Application

### Option 1: Run in Separate Terminals

**Terminal 1 - Start Backend Server:**
```bash
cd server
npm start
```
The server will run on `http://localhost:3000`

**Terminal 2 - Start Frontend Development Server:**
```bash
cd client/Opt-Frontend
npm run dev
```
The frontend will typically run on `http://localhost:5173`

### Option 2: Using VS Code Tasks (Recommended)

Configure VS Code tasks to run both servers simultaneously. Create a `.vscode/tasks.json` file with compound tasks.

## How to Use

1. Open your browser and navigate to the frontend URL (typically `http://localhost:5173`)
2. Click the **"Run Simulation"** button
3. The Python simulation will execute on the backend
4. Once complete, the generated graphs will be displayed
5. Use the navigation buttons to browse through different graphs
6. Click on thumbnails at the bottom to jump to a specific graph

## Features

- **Automatic Graph Generation**: Runs Python simulation and converts outputs to images
- **Interactive Graph Viewer**: 
  - Navigate between graphs with Previous/Next buttons
  - Click thumbnails to jump to specific graphs
  - View graph counter showing current position
- **Error Handling**: Clear error messages if simulation fails
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Feedback**: Shows loading spinner during execution

## Graph Outputs

The simulation generates 4 graphs:

1. **Network Animation** - Shows traffic flow and vehicle movement
2. **Path Demands** - Illustrates demand distribution across routes
3. **Link Densities** - Displays traffic density evolution over time
4. **Charging Station Metrics** - Shows queue lengths, waiting times, utilization rates, and market share

## Troubleshooting

### "Connection refused" Error
- Ensure the backend server is running on port 3000
- Check that no other service is using port 3000
- Verify CORS is enabled in server.js

### "Python not found" Error
- Verify Python is installed: `python --version`
- Ensure Python is in your system PATH
- Try using `python3` instead of `python`

### Missing Python Dependencies
```bash
pip install networkx numpy matplotlib scipy
```

### Graphs Not Displaying
1. Check browser console for errors (F12 → Console tab)
2. Check server logs for Python errors
3. Verify all Python dependencies are installed
4. Ensure simulation completes without errors

## Development

### Modifying the Simulation

Edit `ev_tc_1.py` to change:
- Network topology
- Demand parameters
- Charging station configurations
- Simulation parameters (T_FINAL, N_TIME_POINTS, etc.)

### Customizing the UI

Edit `client/Opt-Frontend/src/App.jsx` and `App.css` to customize:
- Colors and styling
- Button labels
- Graph layout and sizing
- Error messages

## API Endpoints

### POST `/api/run-simulation`

Executes the Python simulation and returns graph images.

**Response:**
```json
{
  "success": true,
  "message": "Simulation completed successfully",
  "graphs": [
    "base64_encoded_image_1",
    "base64_encoded_image_2",
    ...
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Error description",
  "graphs": []
}
```

## Performance Notes

- First run may take 10-30 seconds depending on system performance
- Simulation time depends on:
  - Network complexity
  - Number of paths enumerated
  - Time points (N_TIME_POINTS parameter)
  - Solver tolerance settings

## License

This project is provided as-is for educational and research purposes.
