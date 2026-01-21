import { useState } from 'react'
import './App.css'

function App() {
  const [isRunning, setIsRunning] = useState(false)
  const [graphs, setGraphs] = useState([])
  const [animation, setAnimation] = useState(null)
  const [error, setError] = useState(null)
  const [currentGraphIndex, setCurrentGraphIndex] = useState(0)
  const [showAnimation, setShowAnimation] = useState(true)

  const runSimulation = async () => {
    setIsRunning(true)
    setError(null)
    setGraphs([])
    setAnimation(null)
    setCurrentGraphIndex(0)
    setShowAnimation(true)

    try {
      console.log('Starting simulation...')
      const response = await fetch('http://localhost:3000/api/run-simulation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      console.log('Response status:', response.status)

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()
      console.log('Response data:', data)

      if (data.success && data.data) {
        // Handle graphs
        const graphsArray = data.data.graphs || data.graphs || []
        // Handle animation GIF
        const animationData = data.data.animation || null
        
        if (animationData) {
          console.log('Received animation GIF')
          setAnimation(animationData)
        }
        
        if (graphsArray.length > 0) {
          console.log(`Received ${graphsArray.length} graphs`)
          setGraphs(graphsArray)
          setCurrentGraphIndex(0)
        } else if (!animationData) {
          setError(`No graphs generated. Message: ${data.data.message || 'Unknown'}`)
        }
      } else if (data.data && data.data.message) {
        setError(`Simulation failed: ${data.data.message}`)
      } else {
        setError(data.error || data.message || 'No graphs generated')
      }
    } catch (err) {
      console.error('Error:', err)
      setError(`Error: ${err.message}. Make sure backend is running on localhost:3000`)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="container">
      <header className="header">
        <h1>EV Charging Station Simulation</h1>
        <p>Network-based traffic flow and EV adoption model</p>
      </header>

      <div className="controls">
        <button 
          onClick={runSimulation} 
          disabled={isRunning}
          className="run-button"
        >
          {isRunning ? (
            <>
              <span className="spinner"></span> Running Simulation...
            </>
          ) : (
            'Run Simulation'
          )}
        </button>
      </div>

      {isRunning && (
        <div className="status-message">
          <span className="status-spinner"></span>
          Starting simulation... This may take 10-30 seconds
        </div>
      )}

      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {/* Animation Section */}
      {animation && showAnimation && (
        <div className="results-container">
          <div className="section-header">
            <h2>🎬 Network Animation (100s Simulation)</h2>
            <button 
              className="toggle-button"
              onClick={() => setShowAnimation(false)}
            >
              View Static Graphs →
            </button>
          </div>
          <div className="animation-display">
            <img 
              src={`data:image/gif;base64,${animation}`}
              alt="Network Animation"
              className="animation-image"
            />
          </div>
          <p className="animation-hint">
            ⏱️ Animation shows time-varying x (density) and y (flow) values. Watch values change as simulation progresses!
          </p>
        </div>
      )}

      {/* Static Graphs Section */}
      {graphs.length > 0 && (!animation || !showAnimation) && (
        <div className="results-container">
          {animation && (
            <div className="section-header">
              <h2>📊 Static Analysis Graphs</h2>
              <button 
                className="toggle-button"
                onClick={() => setShowAnimation(true)}
              >
                ← View Animation
              </button>
            </div>
          )}
          <div className="graph-viewer">
            <div className="graph-display">
              <img 
                src={`data:image/png;base64,${graphs[currentGraphIndex]}`}
                alt={`Graph ${currentGraphIndex + 1}`}
                className="graph-image"
              />
            </div>

            <div className="navigation">
              <button 
                onClick={() => setCurrentGraphIndex((i) => Math.max(0, i - 1))}
                disabled={currentGraphIndex === 0}
                className="nav-button prev"
              >
                ← Previous
              </button>

              <div className="counter">
                Graph {currentGraphIndex + 1} of {graphs.length}
              </div>

              <button 
                onClick={() => setCurrentGraphIndex((i) => Math.min(graphs.length - 1, i + 1))}
                disabled={currentGraphIndex === graphs.length - 1}
                className="nav-button next"
              >
                Next →
              </button>
            </div>

            <div className="graph-thumbnails">
              {graphs.map((_, index) => (
                <div
                  key={index}
                  className={`thumbnail ${index === currentGraphIndex ? 'active' : ''}`}
                  onClick={() => setCurrentGraphIndex(index)}
                >
                  <img 
                    src={`data:image/png;base64,${graphs[index]}`}
                    alt={`Thumbnail ${index + 1}`}
                  />
                  <span className="thumb-label">{index + 1}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {graphs.length === 0 && !animation && !isRunning && !error && (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>Click "Run Simulation" to generate graphs</p>
        </div>
      )}
    </div>
  )
}

export default App
