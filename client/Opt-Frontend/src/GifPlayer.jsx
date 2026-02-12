import { useState, useRef, useEffect, useCallback } from 'react'
import { parseGIF, decompressFrames } from 'gifuct-js'

function GifPlayer({ gifBase64, simulationDuration }) {
  const canvasRef = useRef(null)
  const [frames, setFrames] = useState([])
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [totalFrames, setTotalFrames] = useState(0)
  const animationRef = useRef(null)
  const lastTimeRef = useRef(0)
  const frameDelayRef = useRef(100)

  // Parse the GIF and extract frames
  useEffect(() => {
    if (!gifBase64) return

    const parseGifData = async () => {
      setIsLoading(true)
      try {
        // Convert base64 to ArrayBuffer
        const binaryString = atob(gifBase64)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }

        // Parse the GIF
        const gif = parseGIF(bytes.buffer)
        const decompressedFrames = decompressFrames(gif, true)

        if (decompressedFrames.length > 0) {
          // Get frame delay (default 100ms if not specified)
          frameDelayRef.current = decompressedFrames[0].delay || 100
          
          // Create image data for each frame
          const canvas = document.createElement('canvas')
          canvas.width = gif.lsd.width
          canvas.height = gif.lsd.height
          const ctx = canvas.getContext('2d')

          const processedFrames = []
          let previousImageData = null

          for (let i = 0; i < decompressedFrames.length; i++) {
            const frame = decompressedFrames[i]
            
            // Create ImageData from frame patch
            const imageData = ctx.createImageData(gif.lsd.width, gif.lsd.height)
            
            // If we have a previous frame, copy it first (for disposal method)
            if (previousImageData) {
              imageData.data.set(previousImageData.data)
            }

            // Apply the frame patch
            const { patch, dims } = frame
            for (let y = 0; y < dims.height; y++) {
              for (let x = 0; x < dims.width; x++) {
                const patchIdx = (y * dims.width + x) * 4
                const canvasIdx = ((dims.top + y) * gif.lsd.width + (dims.left + x)) * 4
                
                // Only apply non-transparent pixels
                if (patch[patchIdx + 3] !== 0) {
                  imageData.data[canvasIdx] = patch[patchIdx]
                  imageData.data[canvasIdx + 1] = patch[patchIdx + 1]
                  imageData.data[canvasIdx + 2] = patch[patchIdx + 2]
                  imageData.data[canvasIdx + 3] = patch[patchIdx + 3]
                }
              }
            }

            // Store clone of imageData for next frame
            previousImageData = new ImageData(
              new Uint8ClampedArray(imageData.data),
              imageData.width,
              imageData.height
            )

            processedFrames.push({
              imageData: previousImageData,
              delay: frame.delay || 100
            })
          }

          setFrames(processedFrames)
          setTotalFrames(processedFrames.length)
          setCurrentFrame(0)
        }
      } catch (err) {
        console.error('Failed to parse GIF:', err)
      }
      setIsLoading(false)
    }

    parseGifData()
  }, [gifBase64])

  // Render current frame to canvas
  useEffect(() => {
    if (!canvasRef.current || frames.length === 0) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const frame = frames[currentFrame]

    if (frame) {
      canvas.width = frame.imageData.width
      canvas.height = frame.imageData.height
      ctx.putImageData(frame.imageData, 0, 0)
    }
  }, [currentFrame, frames])

  // Animation loop
  useEffect(() => {
    if (!isPlaying || frames.length === 0) return

    const animate = (timestamp) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp

      const elapsed = timestamp - lastTimeRef.current
      const delay = frames[currentFrame]?.delay || frameDelayRef.current

      if (elapsed >= delay) {
        setCurrentFrame(prev => (prev + 1) % frames.length)
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
  }, [isPlaying, frames, currentFrame])

  // Handle play/pause
  const togglePlay = useCallback(() => {
    setIsPlaying(prev => !prev)
    lastTimeRef.current = 0
  }, [])

  // Handle restart
  const handleRestart = useCallback(() => {
    setCurrentFrame(0)
    setIsPlaying(true)
    lastTimeRef.current = 0
  }, [])

  // Handle seek bar click
  const handleSeek = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width
    const frameIndex = Math.floor(percentage * frames.length)
    setCurrentFrame(Math.min(Math.max(0, frameIndex), frames.length - 1))
  }, [frames.length])

  // Handle seek bar drag
  const handleSeekDrag = useCallback((e) => {
    if (e.buttons !== 1) return // Only handle left mouse button
    handleSeek(e)
  }, [handleSeek])

  // Calculate current time based on frame
  const getCurrentTime = () => {
    if (totalFrames === 0) return '0.00s'
    const timePerFrame = simulationDuration / totalFrames
    return `${(currentFrame * timePerFrame).toFixed(2)}s`
  }

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT') return
      
      switch (e.key) {
        case ' ':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          e.preventDefault()
          setCurrentFrame(prev => Math.max(0, prev - 1))
          setIsPlaying(false)
          break
        case 'ArrowRight':
          e.preventDefault()
          setCurrentFrame(prev => Math.min(frames.length - 1, prev + 1))
          setIsPlaying(false)
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePlay, frames.length])

  if (isLoading) {
    return (
      <div className="gif-player-loading">
        <div className="loading-spinner"></div>
        <span>Loading animation frames...</span>
      </div>
    )
  }

  return (
    <div className="gif-player">
      <div className="gif-player-canvas-container" onClick={togglePlay}>
        <canvas ref={canvasRef} className="gif-player-canvas" />
        {!isPlaying && (
          <div className="gif-player-play-overlay">
            <svg viewBox="0 0 24 24" fill="white" width="64" height="64">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
        )}
      </div>

      <div className="gif-player-controls">
        <button className="gif-control-btn" onClick={togglePlay} title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}>
          {isPlaying ? (
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <rect x="6" y="4" width="4" height="16"/>
              <rect x="14" y="4" width="4" height="16"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          )}
        </button>

        <div className="gif-time-display">
          <span className="gif-current-time">{getCurrentTime()}</span>
          <span className="gif-time-separator">/</span>
          <span className="gif-total-time">{simulationDuration}s</span>
        </div>

        <div 
          className="gif-seek-bar" 
          onClick={handleSeek}
          onMouseMove={handleSeekDrag}
        >
          <div className="gif-seek-bar-bg"></div>
          <div 
            className="gif-seek-bar-progress" 
            style={{ width: `${(currentFrame / Math.max(1, totalFrames - 1)) * 100}%` }}
          ></div>
          <div 
            className="gif-seek-bar-handle"
            style={{ left: `${(currentFrame / Math.max(1, totalFrames - 1)) * 100}%` }}
          ></div>
        </div>

        <button className="gif-control-btn" onClick={handleRestart} title="Restart">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
            <path d="M1 4v6h6"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
        </button>

        <a 
          className="gif-control-btn" 
          href={`data:image/gif;base64,${gifBase64}`}
          download="ev_simulation.gif"
          title="Download"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </a>

        <div className="gif-frame-display">
          Frame {currentFrame + 1}/{totalFrames}
        </div>
      </div>

      <div className="gif-player-hint">
        <span>Space: Play/Pause</span>
        <span>←→: Frame by frame</span>
        <span>Click timeline to seek</span>
      </div>
    </div>
  )
}

export default GifPlayer
