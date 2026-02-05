import { useState } from 'react'
import './App.css'

// API URL - uses environment variable in production, localhost in development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'

function App() {
  const [isRunning, setIsRunning] = useState(false)
  const [graphs, setGraphs] = useState([])
  const [animation, setAnimation] = useState(null)
  const [error, setError] = useState(null)
  const [currentGraphIndex, setCurrentGraphIndex] = useState(0)
  const [showAnimation, setShowAnimation] = useState(true)
  const [progress, setProgress] = useState(0)

  const runSimulation = async () => {
    setIsRunning(true)
    setError(null)
    setGraphs([])
    setAnimation(null)
    setCurrentGraphIndex(0)
    setShowAnimation(true)
    setProgress(0)

    // Simulate progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev
        return prev + Math.random() * 15
      })
    }, 500)

    try {
      console.log('Starting simulation...')
      const response = await fetch(`${API_URL}/api/run-simulation`, {
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
      setProgress(100)

      if (data.success && data.data) {
        const graphsArray = data.data.graphs || data.graphs || []
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
      clearInterval(progressInterval)
      setIsRunning(false)
      setProgress(0)
    }
  }

  return (
    <div className="app-wrapper">
      {/* Animated background elements */}
      <div className="bg-decoration">
        <div className="floating-shape shape-1"></div>
        <div className="floating-shape shape-2"></div>
        <div className="floating-shape shape-3"></div>
        <div className="grid-overlay"></div>
      </div>

      <div className="container">
        {/* Header Section */}
        <header className="header">
          <div className="logo-container">
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="logo-text">
              <h1>EV Charging Station</h1>
              <span className="logo-subtitle">Simulation Platform</span>
            </div>
          </div>
          <p className="header-description">
            Advanced network-based traffic flow analysis and EV adoption modeling
          </p>
          <div className="header-badges">
            <span className="badge">🔬 Scientific Analysis</span>
            <span className="badge">📈 Real-time Graphs</span>
            <span className="badge">🎬 Animation Support</span>
          </div>
        </header>

        {/* Control Panel */}
        <div className="control-panel">
          <div className="panel-header">
            <h2>Simulation Control</h2>
            <div className="status-indicator">
              <span className={`status-dot ${isRunning ? 'active' : ''}`}></span>
              <span className="status-text">{isRunning ? 'Running' : 'Ready'}</span>
            </div>
          </div>
          
          <div className="panel-content">
            <div className="info-cards">
              <div className="info-card">
                <div className="info-icon">🚗</div>
                <div className="info-text">
                  <span className="info-label">Model</span>
                  <span className="info-value">Traffic Flow</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">⚡</div>
                <div className="info-text">
                  <span className="info-label">Type</span>
                  <span className="info-value">EV Network</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">⏱️</div>
                <div className="info-text">
                  <span className="info-label">Duration</span>
                  <span className="info-value">100s Sim</span>
                </div>
              </div>
            </div>

            <button 
              onClick={runSimulation} 
              disabled={isRunning}
              className="run-button"
            >
              {isRunning ? (
                <>
                  <span className="btn-spinner"></span>
                  <span>Processing Simulation...</span>
                </>
              ) : (
                <>
                  <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5 3 19 12 5 21 5 3" fill="currentColor"/>
                  </svg>
                  <span>Run Simulation</span>
                </>
              )}
            </button>

            {isRunning && (
              <div className="progress-container">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                </div>
                <span className="progress-text">{Math.round(progress)}% Complete</span>
              </div>
            )}
          </div>
        </div>

        {/* Status Messages */}
        {isRunning && (
          <div className="status-message">
            <div className="status-content">
              <div className="pulse-ring"></div>
              <span className="status-icon">⚙️</span>
              <div className="status-info">
                <span className="status-title">Simulation in Progress</span>
                <span className="status-desc">Computing network dynamics... This may take 10-30 seconds</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            <div className="error-content">
              <span className="error-icon">⚠️</span>
              <div className="error-info">
                <span className="error-title">Simulation Error</span>
                <span className="error-desc">{error}</span>
              </div>
            </div>
            <button className="error-dismiss" onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Animation Section */}
        {animation && showAnimation && (
          <div className="results-container animation-container">
            <div className="results-header">
              <div className="results-title">
                <span className="results-icon">🎬</span>
                <div>
                  <h2>Network Animation</h2>
                  <span className="results-subtitle">100-second simulation visualization</span>
                </div>
              </div>
              <button className="toggle-button" onClick={() => setShowAnimation(false)}>
                <span>View Static Graphs</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 18l6-6-6-6"/>
                </svg>
              </button>
            </div>
            <div className="animation-display">
              <img 
                src={`data:image/gif;base64,${animation}`}
                alt="Network Animation"
                className="animation-image"
              />
            </div>
            <div className="animation-footer">
              <div className="legend-item">
                <span className="legend-color" style={{background: '#3b82f6'}}></span>
                <span>x: Density values</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{background: '#10b981'}}></span>
                <span>y: Flow values</span>
              </div>
            </div>
          </div>
        )}

        {/* Static Graphs Section */}
        {graphs.length > 0 && (!animation || !showAnimation) && (
          <div className="results-container graphs-container">
            <div className="results-header">
              <div className="results-title">
                <span className="results-icon">📊</span>
                <div>
                  <h2>Analysis Results</h2>
                  <span className="results-subtitle">{graphs.length} graphs generated</span>
                </div>
              </div>
              {animation && (
                <button className="toggle-button" onClick={() => setShowAnimation(true)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M15 18l-6-6 6-6"/>
                  </svg>
                  <span>View Animation</span>
                </button>
              )}
            </div>
            
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
                  className="nav-button"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M15 18l-6-6 6-6"/>
                  </svg>
                  <span>Previous</span>
                </button>

                <div className="counter">
                  <span className="counter-current">{currentGraphIndex + 1}</span>
                  <span className="counter-separator">/</span>
                  <span className="counter-total">{graphs.length}</span>
                </div>

                <button 
                  onClick={() => setCurrentGraphIndex((i) => Math.min(graphs.length - 1, i + 1))}
                  disabled={currentGraphIndex === graphs.length - 1}
                  className="nav-button"
                >
                  <span>Next</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 18l6-6-6-6"/>
                  </svg>
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
                    <span className="thumb-number">{index + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {graphs.length === 0 && !animation && !isRunning && !error && (
          <div className="empty-state">
            <div className="empty-visual">
              <div className="empty-circle">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M18 9l-5 5-4-3-3 4" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="empty-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
            <h3>Ready to Simulate</h3>
            <p>Click the "Run Simulation" button above to generate analysis graphs and animations</p>
            <div className="empty-features">
              <div className="feature-item">
                <span className="feature-icon">📈</span>
                <span>Traffic Analysis</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔋</span>
                <span>EV Adoption</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🗺️</span>
                <span>Network Flow</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="footer">
          <p>EV Charging Station Simulation • Network-based Traffic Analysis</p>
        </footer>
      </div>
    </div>
  )
}

export default App
