import { useRef, useState } from 'react'
import { uploadOne } from '../lib/api.js'

const ACCEPT = '.pdf,.docx,.txt'
const MAX_FILES = 100
const ALLOWED_EXT = ['.pdf', '.docx', '.txt']

function statusLabel(s) {
  if (s === 'queued') return 'Queued'
  if (s === 'uploading') return 'Uploading…'
  if (s === 'pending') return 'Ready'
  if (s === 'error') return 'Error'
  return s
}

export default function CVDropZone({ roleId, onUploaded }) {
  const [files, setFiles] = useState([]) // [{file, status, name, candidate_id, error_msg}]
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const addFiles = (incoming) => {
    setError('')
    const arr = Array.from(incoming)
    const accepted = []
    const rejected = []
    for (const f of arr) {
      const lower = f.name.toLowerCase()
      if (ALLOWED_EXT.some((ext) => lower.endsWith(ext))) accepted.push(f)
      else rejected.push(f.name)
    }
    const next = [...files, ...accepted.map((f) => ({ file: f, status: 'queued' }))]
    if (next.length > MAX_FILES) {
      setError(`Max ${MAX_FILES} files. Drop the extras.`)
      next.splice(MAX_FILES)
    }
    if (rejected.length) {
      setError(`Skipped ${rejected.length} unsupported file(s): ${rejected.slice(0, 3).join(', ')}${rejected.length > 3 ? '…' : ''}`)
    }
    setFiles(next)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    if (uploading) return
    addFiles(e.dataTransfer.files)
  }

  const removeFile = (idx) => {
    setFiles(files.filter((_, i) => i !== idx))
  }

  const upload = async () => {
    setError('')
    if (!files.length) return
    setUploading(true)
    setFiles((prev) => prev.map((f) => ({ ...f, status: 'queued' })))
    const results = []
    try {
      for (let idx = 0; idx < files.length; idx++) {
        setFiles((prev) => {
          const copy = [...prev]
          if (copy[idx]) copy[idx] = { ...copy[idx], status: 'uploading' }
          return copy
        })
        let result
        try {
          result = await uploadOne(roleId, files[idx].file)
        } catch (e) {
          result = {
            file_name: files[idx].file.name,
            status: 'error',
            error_msg: e.message || 'Upload failed',
          }
        }
        setFiles((prev) => {
          const copy = [...prev]
          if (copy[idx]) {
            copy[idx] = {
              ...copy[idx],
              status: result.status,
              name: result.name,
              candidate_id: result.candidate_id,
              error_msg: result.error_msg,
            }
          }
          return copy
        })
        results.push(result)
      }
      onUploaded?.(results)
    } catch (e) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const dropZoneStyle = {
    border: `2px dashed ${dragging ? 'var(--color-accent)' : 'var(--color-border-secondary)'}`,
    borderRadius: 12,
    padding: 36,
    textAlign: 'center',
    background: dragging ? 'var(--color-accent-soft)' : 'var(--color-background-secondary)',
    transition: 'background 0.1s ease, border-color 0.1s ease',
    cursor: 'pointer',
  }

  return (
    <div className="stack-lg">
      <div
        style={dropZoneStyle}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          style={{ display: 'none' }}
          onChange={(e) => addFiles(e.target.files)}
        />
        <div className="h2">Drop CVs here or click to browse</div>
        <div className="muted">.pdf, .docx, .txt &middot; up to {MAX_FILES} files</div>
      </div>

      {error && <div className="error">{error}</div>}

      {!!files.length && (
        <div className="card stack">
          <div className="row">
            <div className="h2">{files.length} file{files.length === 1 ? '' : 's'} queued</div>
            <div className="spacer" />
            <button className="primary" onClick={upload} disabled={uploading}>
              {uploading ? <><span className="spinner" /> &nbsp;Uploading…</> : `Upload ${files.length} CV${files.length === 1 ? '' : 's'}`}
            </button>
          </div>
          <div className="stack" style={{ maxHeight: 320, overflowY: 'auto' }}>
            {files.map((f, idx) => (
              <div key={idx} className="row" style={{ gap: 10, fontSize: 13 }}>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {f.file.name}
                </span>
                <span className="muted" style={{ minWidth: 60, textAlign: 'right' }}>
                  {(f.file.size / 1024).toFixed(0)} KB
                </span>
                <span className={
                  f.status === 'error' ? 'badge reject'
                    : f.status === 'pending' ? 'badge teal'
                    : 'badge muted'
                } style={{ minWidth: 80, justifyContent: 'center' }}>
                  {statusLabel(f.status)}
                </span>
                {!uploading && (
                  <button onClick={() => removeFile(idx)} style={{ padding: '4px 8px' }}>×</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
