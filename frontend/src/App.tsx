import { useEffect, useRef, useState, useCallback } from 'react'
import { fetchProcessors, streamVideo, processImage, ProcessorMeta } from './api'
import './App.css'

type Status = 'idle' | 'loading' | 'streaming' | 'done' | 'error'
type FileMode = 'video' | 'image'

function App() {
  const [processors, setProcessors] = useState<ProcessorMeta[]>([])
  const [selectedProcessor, setSelectedProcessor] = useState<string>('')
  const [status, setStatus] = useState<Status>('idle')
  const [progress, setProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 })
  const [currentProcessedFrame, setCurrentProcessedFrame] = useState<string>('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [originalUrl, setOriginalUrl] = useState<string>('')
  const [fileMode, setFileMode] = useState<FileMode>('video')

  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    fetchProcessors()
      .then((list) => {
        setProcessors(list)
        if (list.length > 0) setSelectedProcessor(list[0].id)
      })
      .catch(() => setProcessors([]))
  }, [])

  useEffect(() => {
    return () => { if (originalUrl) URL.revokeObjectURL(originalUrl) }
  }, [originalUrl])

  const resetState = useCallback(() => {
    setCurrentProcessedFrame('')
    setStatus('idle')
    setProgress({ current: 0, total: 0 })
  }, [])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Detect file mode from MIME type
    const mode: FileMode = file.type.startsWith('image/') ? 'image' : 'video'
    setFileMode(mode)
    setSelectedFile(file)

    if (originalUrl) URL.revokeObjectURL(originalUrl)
    setOriginalUrl(URL.createObjectURL(file))
    resetState()
  }, [originalUrl, resetState])

  const handleProcess = useCallback(async () => {
    if (!selectedFile || !selectedProcessor) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStatus('loading')
    setCurrentProcessedFrame('')
    setProgress({ current: 0, total: 0 })

    if (fileMode === 'image') {
      // Single-shot image processing
      await processImage(
        selectedFile,
        selectedProcessor,
        (dataUrl) => {
          setCurrentProcessedFrame(dataUrl)
          setStatus('done')
          setProgress({ current: 1, total: 1 })
        },
        () => setStatus('error'),
        controller.signal,
      )
    } else {
      // Streaming video processing
      await streamVideo(
        selectedFile,
        selectedProcessor,
        (payload) => {
          setStatus('streaming')
          setCurrentProcessedFrame(`data:image/jpeg;base64,${payload.frame}`)
          setProgress({ current: payload.index + 1, total: payload.total })
        },
        (total) => {
          setStatus('done')
          setProgress((p) => ({ ...p, total }))
        },
        () => setStatus('error'),
        controller.signal,
      )
    }
  }, [selectedFile, selectedProcessor, fileMode])

  const handleStop = useCallback(() => {
    abortRef.current?.abort()
    setStatus('idle')
  }, [])

  const selectedMeta = processors.find((p) => p.id === selectedProcessor)
  const isProcessing = status === 'loading' || status === 'streaming'
  const progressPercent = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0

  return (
    <div className="app">
      <header className="app-header">
        <h1>CV Showcase</h1>
        <p className="app-subtitle">
          Select a CV filter, upload an image or video, and see it processed in real-time.
        </p>
      </header>

      <main className="app-main">

        {/* ── Controls ───────────────────────────────────────────── */}
        <section className="controls" aria-label="Processing controls">

          <label htmlFor="processor-select" className="control-label">CV Filter</label>
          <label htmlFor="file-input" className="control-label">
            File
            {selectedFile && (
              <span className="file-mode-badge">
                {fileMode === 'image' ? 'image' : 'video'}
              </span>
            )}
          </label>
          <div className="control-label" aria-hidden="true" />

          <select
            id="processor-select"
            value={selectedProcessor}
            onChange={(e) => setSelectedProcessor(e.target.value)}
            disabled={isProcessing}
          >
            {processors.length === 0
              ? <option value="">Loading filters...</option>
              : processors.map((p) => (
                  <option key={p.id} value={p.id}>{p.label}</option>
                ))
            }
          </select>

          <div className="file-input-wrapper">
            <label
              htmlFor="file-input"
              className={`file-input-label ${isProcessing ? 'disabled' : ''}`}
              aria-disabled={isProcessing}
            >
              {selectedFile ? selectedFile.name : 'Choose image or video…'}
            </label>
            <input
              id="file-input"
              type="file"
              accept="video/mp4,video/webm,video/quicktime,video/x-msvideo,image/jpeg,image/png,image/webp,image/gif"
              onChange={handleFileChange}
              disabled={isProcessing}
              className="file-input-hidden"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            {!isProcessing ? (
              <button
                onClick={handleProcess}
                disabled={!selectedFile || !selectedProcessor}
                className="btn btn-primary"
              >
                {fileMode === 'image' ? 'Process Image' : 'Process Video'}
              </button>
            ) : (
              <button onClick={handleStop} className="btn btn-danger">
                Stop
              </button>
            )}
          </div>

        </section>

        {/* ── Disclaimer ─────────────────────────────────────────── */}
        <p className="disclaimer" role="note">
          Uploaded files are processed in memory and are not saved or stored.
        </p>

        {/* ── Progress bar ───────────────────────────────────────── */}
        {(isProcessing || status === 'done') && (
          <div
            className={`progress-bar ${status === 'loading' ? 'progress-bar--indeterminate' : ''}`}
            role="progressbar"
            aria-valuenow={progressPercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Processing progress"
          >
            <div
              className="progress-fill"
              style={{ width: status === 'loading' ? '100%' : `${progressPercent}%` }}
            />
            <span className="progress-label">
              {status === 'loading' && 'Processing…'}
              {status === 'streaming' && `Frame ${progress.current} of ${progress.total}`}
              {status === 'done' && fileMode === 'image' && '✓ Done'}
              {status === 'done' && fileMode === 'video' && `✓ Done — ${progress.total} frames`}
            </span>
          </div>
        )}

        {/* ── Error banner ───────────────────────────────────────── */}
        {status === 'error' && (
          <div className="error-banner" role="alert">
            <span>Something went wrong. Please try again.</span>
            <button onClick={resetState} className="btn btn-ghost">Try again</button>
          </div>
        )}

        {/* ── Dual display panels ────────────────────────────────── */}
        <section className="display-grid" aria-label="File comparison">

          <div className="display-panel">
            <h2 className="panel-title">Original</h2>
            {originalUrl
              ? fileMode === 'image'
                ? <img src={originalUrl} alt="Original" className="display-media" />
                : <video src={originalUrl} controls className="display-media" aria-label="Original video" />
              : <div className="display-placeholder">Upload an image or video to get started</div>
            }
          </div>

          <div className="display-panel">
            <h2 className="panel-title">
              {selectedMeta ? selectedMeta.label : 'Processed'}
            </h2>
            {isProcessing && !currentProcessedFrame
              ? <div className="display-placeholder"><span className="spinner" aria-label="Processing" /></div>
              : currentProcessedFrame
                ? <img src={currentProcessedFrame} alt="Processed output" className="display-media" />
                : <div className="display-placeholder">
                    {status === 'done' ? 'Processing complete' : 'Output will appear here'}
                  </div>
            }
          </div>

        </section>

        {/* ── About this filter ──────────────────────────────────── */}
        {selectedMeta && (
          <section className="processor-info" aria-label="About this filter">
            <h3>{selectedMeta.label}</h3>
            <p>{selectedMeta.description}</p>
          </section>
        )}

      </main>
    </div>
  )
}

export default App
