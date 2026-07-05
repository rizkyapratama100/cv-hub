// In development the Vite proxy rewrites relative paths to the backend container.
// In production (Cloudflare Pages) VITE_API_URL is set to the Lightsail backend URL.
const API_URL = import.meta.env.VITE_API_URL ?? ''

export interface ProcessorMeta {
  id: string
  label: string
  description: string
}

export interface FramePayload {
  frame: string   // base64 JPEG
  index: number
  total: number
}

export interface DonePayload {
  done: true
  total: number
}

export interface ErrorPayload {
  error: string
}

export type StreamChunk = FramePayload | DonePayload | ErrorPayload

export async function fetchProcessors(): Promise<ProcessorMeta[]> {

  const res = await fetch(`${API_URL}/processors`)
  if (!res.ok) throw new Error(`Failed to fetch processors: ${res.status}`)
  const data = await res.json()
  return data.processors as ProcessorMeta[]
}

/**
 * Upload a video file and stream back processed frames.
 * Calls onFrame for each frame chunk, onDone when complete, onError on failure.
 */
export async function streamVideo(
  file: File,
  processorId: string,
  onFrame: (payload: FramePayload) => void,
  onDone: (total: number) => void,
  onError: (message: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('processor', processorId)

  let res: Response
  try {
    res = await fetch(`${API_URL}/process-video`, {
      method: 'POST',
      body: form,
      signal,
    })
  } catch (err) {
    if ((err as Error).name === 'AbortError') return
    onError('Could not reach the backend. Please try again.')
    return
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    onError(body.detail ?? 'Something went wrong.')
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    onError('Streaming not supported by this browser.')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // NDJSON: split on newlines and process complete lines
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''  // keep incomplete last line

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      try {
        const chunk = JSON.parse(trimmed) as StreamChunk
        if ('error' in chunk) {
          onError(chunk.error)
          return
        } else if ('done' in chunk) {
          onDone(chunk.total)
          return
        } else {
          onFrame(chunk)
        }
      } catch {
        // Malformed JSON line — skip silently
      }
    }
  }
}


/**
 * Upload a single image and return the processed result as a base64 data URL.
 */
export async function processImage(
  file: File,
  processorId: string,
  onResult: (dataUrl: string) => void,
  onError: (message: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('processor', processorId)

  let res: Response
  try {
    res = await fetch(`${API_URL}/process-image`, {
      method: 'POST',
      body: form,
      signal,
    })
  } catch (err) {
    if ((err as Error).name === 'AbortError') return
    onError('Could not reach the backend. Please try again.')
    return
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    onError(body.detail ?? 'Something went wrong.')
    return
  }

  const data = await res.json()
  onResult(`data:image/jpeg;base64,${data.frame}`)
}
