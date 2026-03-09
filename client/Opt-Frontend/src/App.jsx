import { useState } from 'react'
import './App.css'
import GifPlayer from './GifPlayer'
import InteractiveNetworkPlayer from './InteractiveNetworkPlayer'

// API URL - uses environment variable in production, localhost in development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'

function App() {
  const [isRunning, setIsRunning] = useState(false)
  const [graphs, setGraphs] = useState([])
  const [animation, setAnimation] = useState(null)
  const [networkData, setNetworkData] = useState(null)
  const [error, setError] = useState(null)
  const [currentGraphIndex, setCurrentGraphIndex] = useState(0)
  const [showAnimation, setShowAnimation] = useState(true)
  const [viewMode, setViewMode] = useState('animation') // 'animation', 'interactive', 'static'
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(70)
  const [points, setPoints] = useState(400)
  const [simType, setSimType] = useState('tc7') // 'tc7' or 'tc9'

  const runSimulation = async () => {
    setIsRunning(true)
    setError(null)
    setGraphs([])
    setAnimation(null)
    setNetworkData(null)
    setCurrentGraphIndex(0)
    setShowAnimation(true)
    setViewMode('interactive')
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
      console.log(`Parameters: duration=${duration}s, points=${points}, type=${simType}`)
      const response = await fetch(`${API_URL}/api/run-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          duration: duration,
          points: points,
          simType: simType
        })
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
        const networkDataFromServer = data.data.networkData || null
        
        if (animationData) {
          console.log('Received animation GIF')
          setAnimation(animationData)
        }

        if (networkDataFromServer) {
          console.log('Received network data for interactive visualization')
          setNetworkData(networkDataFromServer)
          setViewMode('interactive')
        }
        
        if (graphsArray.length > 0) {
          console.log(`Received ${graphsArray.length} graphs`)
          setGraphs(graphsArray)
          setCurrentGraphIndex(0)
        } else if (!animationData && !networkDataFromServer) {
          setError(`No graphs generated. Message: ${data.data.message || 'Unknown'}`)
        }
      } else if (data.data && data.data.message) {
        setError(`Simulation failed: ${data.data.message}`)
      } else {
        setError(data.error || data.message || 'No graphs generated')
      }
    } catch (err) {
      console.error('Error:', err)
      const apiUrl = API_URL || 'not configured'
      setError(`Error: ${err.message}. Backend URL: ${apiUrl}. Check if VITE_API_URL is correctly set in .env.production`)
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
              <h1>Dynamic Pricing by EV Charging Stations</h1>
              <span className="logo-subtitle">Simulation Platform</span>
            </div>
          </div>
          <p className="header-description">
            Visualization of the impact of dynamic pricing by EV charging stations
          </p>
          <div className="header-badges">
            <span className="badge">� Dynamic traffic flow model</span>
            <span className="badge">⏱️ Queuing Dynamics</span>
            <span className="badge">💰 Charging station revenue</span>
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
            </div>

            {/* Simulation Type Selector */}
            <div className="sim-type-selector">
              <label className="sim-type-label">Network Configuration</label>
              <div className="sim-type-options">
                <button
                  className={`sim-type-btn ${simType === 'tc7' ? 'active' : ''}`}
                  onClick={() => setSimType('tc7')}
                  disabled={isRunning}
                >
                  <span className="sim-type-icon">🔷</span>
                  <span className="sim-type-name">TC-7</span>
                  <span className="sim-type-desc">4 Nodes, 2 Stations</span>
                </button>
                <button
                  className={`sim-type-btn ${simType === 'tc9' ? 'active' : ''}`}
                  onClick={() => setSimType('tc9')}
                  disabled={isRunning}
                >
                  <span className="sim-type-icon">🔶</span>
                  <span className="sim-type-name">TC-9</span>
                  <span className="sim-type-desc">9 Nodes, 4 Stations</span>
                </button>
              </div>
            </div>

            <div className="param-inputs">
              <div className="param-input-group">
                <label htmlFor="duration">Duration (seconds)</label>
                <input
                  type="number"
                  id="duration"
                  value={duration}
                  onChange={(e) => setDuration(Math.max(10, Math.min(400, parseInt(e.target.value) || 100)))}
                  min="10"
                  max="400"
                  disabled={isRunning}
                />
              </div>
              <div className="param-input-group">
                <label htmlFor="points">Time Points</label>
                <input
                  type="number"
                  id="points"
                  value={points}
                  onChange={(e) => setPoints(Math.max(50, Math.min(1000, parseInt(e.target.value) || 400)))}
                  min="50"
                  max="1000"
                  disabled={isRunning}
                />
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

        {/* Results View Mode Selector and Display */}
        {(animation || networkData || graphs.length > 0) && (
          <div className="results-container">
            <div className="results-header">
              <div className="results-title">
                <span className="results-icon">{viewMode === 'interactive' ? '🔗' : viewMode === 'animation' ? '🎬' : '📊'}</span>
                <div>
                  <h2>{viewMode === 'interactive' ? 'Interactive Network' : viewMode === 'animation' ? 'Network Animation' : 'Analysis Results'}</h2>
                  <span className="results-subtitle">{duration}-second simulation</span>
                </div>
              </div>
              
              {/* View Mode Switcher */}
              <div className="view-mode-switcher">
                {networkData && (
                  <button
                    className={`view-mode-btn ${viewMode === 'interactive' ? 'active' : ''}`}
                    onClick={() => setViewMode('interactive')}
                  >
                    🔗 Interactive
                  </button>
                )}
                {animation && (
                  <button
                    className={`view-mode-btn ${viewMode === 'animation' ? 'active' : ''}`}
                    onClick={() => setViewMode('animation')}
                  >
                    🎬 Animation
                  </button>
                )}
                {graphs.length > 0 && (
                  <button
                    className={`view-mode-btn ${viewMode === 'static' ? 'active' : ''}`}
                    onClick={() => setViewMode('static')}
                  >
                    📊 Graphs
                  </button>
                )}
              </div>
            </div>

            {/* Interactive Network View */}
            {viewMode === 'interactive' && networkData && (
              <InteractiveNetworkPlayer 
                networkData={networkData}
                simulationDuration={duration}
              />
            )}

            {/* Animation View */}
            {viewMode === 'animation' && animation && (
              <>
                <div className="animation-display">
                  <GifPlayer gifBase64={animation} simulationDuration={duration} />
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
              </>
            )}

            {/* Static Graphs View */}
            {viewMode === 'static' && graphs.length > 0 && (
              <div className="graph-viewer">
                <div className="graph-header">
                  <h3 className="graph-title">
                    {['Competition Metrics (Dynamic Pricing Game)', 'Path Demand Dynamics', 'Replicator Convergence'][currentGraphIndex] || `Analysis Graph ${currentGraphIndex + 1}`}
                  </h3>
                  <p className="graph-subtitle">
                    {['Market share, pricing strategy, queue lengths, revenue & profit analysis', 
                      'Path flow distribution across OD pairs for NEV and EV', 
                      'τ_avg - τ_p convergence to equilibrium'][currentGraphIndex] || 'Simulation results visualization'}
                  </p>
                </div>
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
                      className={`thumbnail-card ${index === currentGraphIndex ? 'active' : ''}`}
                      onClick={() => setCurrentGraphIndex(index)}
                    >
                      <div className="thumbnail">
                        <img 
                          src={`data:image/png;base64,${graphs[index]}`}
                          alt={`Thumbnail ${index + 1}`}
                        />
                      </div>
                      <span className="thumb-label">
                        {['Competition', 'Path Demand', 'Convergence'][index] || `Graph ${index + 1}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {graphs.length === 0 && !animation && !networkData && !isRunning && !error && (
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
                <span className="feature-icon">�</span>
                <span>Charging station revenue</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🚗</span>
                <span>EV user behavior</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🛣️</span>
                <span>Traffic flow on transportation network</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="footer">
          <p>Simulation platform to visualize the impact of dynamic pricing by EV charging stations on traffic flow, waiting time and charging station revenue</p>
          <div className="footer-credit">
            <p>Developed by <strong>Saswat Padhy</strong>, <strong>Kshitij Mehta</strong> & <strong>Aaditya Chari</strong> as Part of ANRF Funded MAHA-EV Project</p>
            <p>Advisors: Department of Electrical Engineering, IIT Kharagpur, Prof. Ashish R. Hota and Prof. Debaprasad Kastha</p>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default App
