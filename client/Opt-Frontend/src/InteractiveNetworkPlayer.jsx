import { useState, useEffect, useRef, useCallback } from 'react'

function InteractiveNetworkPlayer({ networkData, simulationDuration }) {
  const svgRef = useRef(null)
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [selectedLink, setSelectedLink] = useState(null)
  const [nodePositions, setNodePositions] = useState({})
  const [draggedNode, setDraggedNode] = useState(null)
  const animationRef = useRef(null)
  const lastTimeRef = useRef(0)

  // Initialize node positions from network data
  useEffect(() => {
    if (!networkData?.nodes) return
    
    const positions = {}
    networkData.nodes.forEach(node => {
      positions[node.id] = { x: node.x, y: node.y }
    })
    setNodePositions(positions)
  }, [networkData])

  // Animation loop
  useEffect(() => {
    if (!isPlaying || !networkData?.timePoints) return

    const animate = (timestamp) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp

      const elapsed = timestamp - lastTimeRef.current
      const delay = 100 // 100ms per frame

      if (elapsed >= delay) {
        setCurrentTimeIndex(prev => {
          const next = prev + 1
          if (next >= networkData.timePoints.length) {
            setIsPlaying(false)
            return 0
          }
          return next
        })
        lastTimeRef.current = timestamp
      }

      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isPlaying, networkData])

  const handlePlay = () => {
    setIsPlaying(true)
    lastTimeRef.current = 0
  }

  const handlePause = () => {
    setIsPlaying(false)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setCurrentTimeIndex(0)
    lastTimeRef.current = 0
  }

  const handleSliderChange = (e) => {
    const value = parseInt(e.target.value)
    setCurrentTimeIndex(value)
    setIsPlaying(false)
  }

  const handleLinkClick = (edge) => {
    setSelectedLink(selectedLink?.id === edge.id ? null : edge)
  }

  // Get current density for a link
  const getDensity = (linkId) => {
    if (!networkData?.densities || !networkData.densities[linkId]) return 0
    return networkData.densities[linkId][currentTimeIndex] || 0
  }

  // Get current price for a station
  const getStationPrice = (stationId) => {
    if (!networkData?.stationPrices || !networkData.stationPrices[stationId]) return 0
    return networkData.stationPrices[stationId][currentTimeIndex] || 0
  }

  // Calculate edge path with curve for parallel edges
  const getEdgePath = (source, target, key, isParallel) => {
    const src = nodePositions[source]
    const tgt = nodePositions[target]
    if (!src || !tgt) return ''

    // Scale positions to SVG coordinates
    const scale = 80
    const offsetX = 120
    const offsetY = 240
    
    const x1 = src.x * scale + offsetX
    const y1 = (8 - src.y) * scale + offsetY  // Flip Y
    const x2 = tgt.x * scale + offsetX
    const y2 = (8 - tgt.y) * scale + offsetY

    if (!isParallel) {
      return `M ${x1} ${y1} L ${x2} ${y2}`
    }

    // Create curved path for parallel edges
    const midX = (x1 + x2) / 2
    const midY = (y1 + y2) / 2
    const dx = x2 - x1
    const dy = y2 - y1
    const len = Math.sqrt(dx * dx + dy * dy)
    const perpX = -dy / len
    const perpY = dx / len
    const curveOffset = key === 0 ? 25 : -25
    const ctrlX = midX + perpX * curveOffset
    const ctrlY = midY + perpY * curveOffset

    return `M ${x1} ${y1} Q ${ctrlX} ${ctrlY} ${x2} ${y2}`
  }

  // Get label position along edge
  const getLabelPosition = (source, target, key, isParallel) => {
    const src = nodePositions[source]
    const tgt = nodePositions[target]
    if (!src || !tgt) return { x: 0, y: 0 }

    const scale = 80
    const offsetX = 120
    const offsetY = 240
    
    const x1 = src.x * scale + offsetX
    const y1 = (8 - src.y) * scale + offsetY
    const x2 = tgt.x * scale + offsetX
    const y2 = (8 - tgt.y) * scale + offsetY

    let midX = (x1 + x2) / 2
    let midY = (y1 + y2) / 2

    if (isParallel) {
      const dx = x2 - x1
      const dy = y2 - y1
      const len = Math.sqrt(dx * dx + dy * dy) || 1
      const perpX = -dy / len
      const perpY = dx / len
      const curveOffset = key === 0 ? 20 : -20
      midX += perpX * curveOffset
      midY += perpY * curveOffset
    }

    return { x: midX, y: midY }
  }

  // Check if there are parallel edges
  const hasParallelEdge = (source, target) => {
    if (!networkData?.edges) return false
    return networkData.edges.filter(e => e.source === source && e.target === target).length > 1
  }

  // Handle node drag
  const handleNodeMouseDown = (nodeId, e) => {
    e.stopPropagation()
    setDraggedNode(nodeId)
  }

  const handleMouseMove = useCallback((e) => {
    if (!draggedNode || !svgRef.current) return

    const svg = svgRef.current
    const rect = svg.getBoundingClientRect()
    const scale = 80
    const offsetX = 120
    const offsetY = 240

    const x = ((e.clientX - rect.left) / rect.width * 1000 - offsetX) / scale
    const y = 8 - ((e.clientY - rect.top) / rect.height * 1000 - offsetY) / scale

    setNodePositions(prev => ({
      ...prev,
      [draggedNode]: { x, y }
    }))
  }, [draggedNode])

  const handleMouseUp = useCallback(() => {
    setDraggedNode(null)
  }, [])

  useEffect(() => {
    if (draggedNode) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      return () => {
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [draggedNode, handleMouseMove, handleMouseUp])

  if (!networkData) {
    return <div className="interactive-network-loading">Loading network data...</div>
  }

  const currentTime = networkData.timePoints?.[currentTimeIndex] || 0
  const totalFrames = networkData.timePoints?.length || 1

  return (
    <div className="interactive-network-container">
      <div className="network-main">
        {/* SVG Network Visualization */}
        <div className="network-svg-container">
          <h3 className="network-title">
            Network Simulation &nbsp; t = {currentTime.toFixed(1)} s
          </h3>
          
          <svg 
            ref={svgRef}
            className="network-svg"
            viewBox="0 0 1000 1000"
            preserveAspectRatio="xMidYMid meet"
          >
            {/* Define arrow marker */}
            <defs>
              <marker
                id="arrowhead-black"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#2c3e50" />
              </marker>
              <marker
                id="arrowhead-green"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#27ae60" />
              </marker>
            </defs>

            {/* Draw edges */}
            {networkData.edges?.map((edge) => {
              const isParallel = hasParallelEdge(edge.source, edge.target)
              const density = getDensity(edge.id)
              const isEVOnly = edge.linkType === 'EV-only'
              const isSelected = selectedLink?.id === edge.id
              const strokeWidth = 2 + density * 4
              
              return (
                <g key={`edge-${edge.id}`} className="network-edge-group">
                  {/* Clickable area (wider for easier clicking) */}
                  <path
                    d={getEdgePath(edge.source, edge.target, edge.key, isParallel)}
                    fill="none"
                    stroke="transparent"
                    strokeWidth={20}
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleLinkClick(edge)}
                  />
                  {/* Visible edge */}
                  <path
                    d={getEdgePath(edge.source, edge.target, edge.key, isParallel)}
                    fill="none"
                    stroke={isSelected ? '#e74c3c' : (isEVOnly ? '#27ae60' : '#2c3e50')}
                    strokeWidth={strokeWidth}
                    strokeDasharray={isEVOnly ? '8,4' : 'none'}
                    markerEnd={isEVOnly ? 'url(#arrowhead-green)' : 'url(#arrowhead-black)'}
                    style={{ 
                      cursor: 'pointer',
                      opacity: selectedLink && !isSelected ? 0.3 : 1,
                      transition: 'opacity 0.2s, stroke 0.2s'
                    }}
                    onClick={() => handleLinkClick(edge)}
                  />
                  {/* Edge label */}
                  {(() => {
                    const pos = getLabelPosition(edge.source, edge.target, edge.key, isParallel)
                    return (
                      <g transform={`translate(${pos.x}, ${pos.y})`}>
                        <rect
                          x={-45}
                          y={-26}
                          width={90}
                          height={52}
                          rx={8}
                          fill={isEVOnly ? '#d5f5e3' : 'white'}
                          stroke={isSelected ? '#e74c3c' : (isEVOnly ? '#27ae60' : '#2c3e50')}
                          strokeWidth={isSelected ? 3 : 2}
                          style={{ cursor: 'pointer' }}
                          onClick={() => handleLinkClick(edge)}
                        />
                        <text
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize="18"
                          fontWeight="bold"
                          fill="#333"
                          style={{ cursor: 'pointer', userSelect: 'none' }}
                          onClick={() => handleLinkClick(edge)}
                        >
                          {edge.stationId || `L${edge.id}`}
                        </text>
                        <text
                          y={17}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize="15"
                          fill="#666"
                          style={{ cursor: 'pointer', userSelect: 'none' }}
                          onClick={() => handleLinkClick(edge)}
                        >
                          x:{density.toFixed(2)}
                        </text>
                      </g>
                    )
                  })()}
                </g>
              )
            })}

            {/* Draw nodes */}
            {networkData.nodes?.map((node) => {
              const pos = nodePositions[node.id]
              if (!pos) return null
              
              const scale = 80
              const offsetX = 120
              const offsetY = 240
              const x = pos.x * scale + offsetX
              const y = (8 - pos.y) * scale + offsetY
              
              let fillColor = '#9ca3af'
              let strokeColor = '#374151'
              
              if (node.type === 'origin') {
                fillColor = '#3b82f6'
                strokeColor = '#1e40af'
              } else if (node.type === 'destination') {
                fillColor = '#ef4444'
                strokeColor = '#b91c1c'
              }
              
              return (
                <g 
                  key={`node-${node.id}`} 
                  className="network-node-group"
                  style={{ cursor: 'grab' }}
                  onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                >
                  <circle
                    cx={x}
                    cy={y}
                    r={35}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={4}
                  />
                  <text
                    x={x}
                    y={y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    fontSize="22"
                    fontWeight="bold"
                    style={{ userSelect: 'none', pointerEvents: 'none' }}
                  >
                    {node.id}
                  </text>
                </g>
              )
            })}
          </svg>

          {/* Legend */}
          <div className="network-legend">
            <div className="legend-item">
              <div className="legend-line" style={{ backgroundColor: '#2c3e50' }}></div>
              <span>Mixed link</span>
            </div>
            <div className="legend-item">
              <div className="legend-line dashed" style={{ backgroundColor: '#27ae60' }}></div>
              <span>EV-only link (charging)</span>
            </div>
            <div className="legend-item">
              <div className="legend-circle" style={{ backgroundColor: '#3b82f6' }}></div>
              <span>Origin node</span>
            </div>
            <div className="legend-item">
              <div className="legend-circle" style={{ backgroundColor: '#ef4444' }}></div>
              <span>Destination node</span>
            </div>
          </div>

          {/* Controls */}
          <div className="network-controls">
            <button 
              className={`control-btn play ${isPlaying ? '' : 'active'}`}
              onClick={handlePlay}
              disabled={isPlaying}
            >
              Play
            </button>
            <button 
              className={`control-btn pause ${isPlaying ? 'active' : ''}`}
              onClick={handlePause}
              disabled={!isPlaying}
            >
              Pause
            </button>
            <button 
              className="control-btn reset"
              onClick={handleReset}
            >
              Reset
            </button>
          </div>

          {/* Timeline slider */}
          <div className="network-timeline">
            <input
              type="range"
              min={0}
              max={totalFrames - 1}
              value={currentTimeIndex}
              onChange={handleSliderChange}
              className="timeline-slider"
            />
            <div className="timeline-info">
              <span>{currentTime.toFixed(1)}s / {simulationDuration}s</span>
              <span>Frame {currentTimeIndex + 1} / {totalFrames}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Link Inspector Panel */}
      <div className="link-inspector">
        <h3 className="inspector-title">Link Inspector</h3>
        
        {selectedLink ? (
          <div className="inspector-content">
            <div className="inspector-header">
              <span className="link-label">{selectedLink.source} → {selectedLink.target}</span>
              <span className="link-id">Link {selectedLink.id} | {selectedLink.linkType}</span>
            </div>
            
            <div className="inspector-divider"></div>
            
            <div className="inspector-row">
              <span className="row-label">Density x<sub>i</sub></span>
              <span className="row-value">{getDensity(selectedLink.id).toFixed(4)}</span>
            </div>
            
            <div className="inspector-row">
              <span className="row-label">Link Type</span>
              <span className="row-value">{selectedLink.linkType}</span>
            </div>
            
            {selectedLink.stationId && (
              <>
                <div className="inspector-divider"></div>
                <div className="inspector-section">
                  <h4>Station: {selectedLink.stationId}</h4>
                  <div className="inspector-row">
                    <span className="row-label">Price p<sub>s</sub></span>
                    <span className="row-value">${getStationPrice(selectedLink.stationId).toFixed(2)}</span>
                  </div>
                </div>
              </>
            )}
            
            <button 
              className="inspector-close"
              onClick={() => setSelectedLink(null)}
            >
              Clear Selection
            </button>
          </div>
        ) : (
          <div className="inspector-empty">
            <p>Click any link to inspect it.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default InteractiveNetworkPlayer
