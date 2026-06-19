import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import CVDropZone from '../components/CVDropZone.jsx'
import { clearCandidates, getCandidates, getPreloadedInfo, loadPreloaded } from '../lib/api.js'

export default function UploadCVs() {
  const { roleId } = useParams()
  const navigate = useNavigate()
  const [uploaded, setUploaded] = useState([])
  const [priorCount, setPriorCount] = useState(0)
  const [clearing, setClearing] = useState(false)
  const [confirmingClear, setConfirmingClear] = useState(false)
  const [preloadInfo, setPreloadInfo] = useState({ available: false, count: 0 })
  const [preloading, setPreloading] = useState(false)
  const [preloadResult, setPreloadResult] = useState(null)
  const [error, setError] = useState('')

  const refreshPriorCount = async () => {
    try {
      const r = await getCandidates(roleId)
      setPriorCount((r.candidates || []).length)
    } catch {
      // non-fatal; banner just won't show
    }
  }

  useEffect(() => {
    refreshPriorCount()
    getPreloadedInfo().then(setPreloadInfo).catch(() => {})
  }, [roleId])

  const handleLoadPreloaded = async () => {
    setError('')
    setPreloading(true)
    setPreloadResult(null)
    try {
      const res = await loadPreloaded(roleId)
      setPreloadResult(res)
      await refreshPriorCount()
    } catch (e) {
      setError(e.message || 'Failed to load pre-cached resumes')
    } finally {
      setPreloading(false)
    }
  }

  const handleClear = async () => {
    setError('')
    setClearing(true)
    try {
      await clearCandidates(roleId)
      setPriorCount(0)
      setUploaded([])
      setConfirmingClear(false)
    } catch (e) {
      setError(e.message || 'Failed to clear candidates')
    } finally {
      setClearing(false)
    }
  }

  const handleContinue = () => {
    navigate(`/role/${roleId}/criteria`)
  }

  const handleUploaded = (results) => {
    setUploaded(results)
    refreshPriorCount()
  }

  // Treat "prior" as anything already in the DB before this session's uploads.
  const sessionUploadCount = uploaded.length
  const showPriorBanner = priorCount > sessionUploadCount && !confirmingClear

  return (
    <>
      <div className="page-header">
        <div>
          <div className="breadcrumb">CV Screener / Upload</div>
          <div className="page-title">Upload candidate CVs</div>
        </div>
        <div className="spacer" />
        <div className="step-indicator" style={{ margin: 0 }}>
          <span className="dot active" /> Step 1 of 3
          <span className="dot" /> Criteria
          <span className="dot" /> Scoring
        </div>
      </div>

      {showPriorBanner && (
        <div className="card session-banner" style={{ marginBottom: 16 }}>
          <div className="row">
            <div>
              <div className="h2" style={{ margin: 0 }}>
                {priorCount} candidate{priorCount === 1 ? '' : 's'} from a previous session
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                Start a fresh session to delete the existing CVs and scores before uploading new ones.
              </div>
            </div>
            <div className="spacer" />
            <button className="primary" onClick={() => setConfirmingClear(true)}>
              Start fresh session
            </button>
          </div>
        </div>
      )}

      {confirmingClear && (
        <div className="card session-banner danger" style={{ marginBottom: 16 }}>
          <div className="row">
            <div>
              <div className="h2" style={{ margin: 0 }}>
                Delete {priorCount} candidate{priorCount === 1 ? '' : 's'}?
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                This permanently removes all CVs, scores, and recommendations for this role. Cannot be undone.
              </div>
            </div>
            <div className="spacer" />
            <button onClick={() => setConfirmingClear(false)} disabled={clearing}>Cancel</button>
            <button className="primary" onClick={handleClear} disabled={clearing}>
              {clearing ? <><span className="spinner" />&nbsp;Deleting…</> : 'Yes, delete all'}
            </button>
          </div>
        </div>
      )}

      {preloadInfo.available && (
        <div className="card preload-banner" style={{ marginBottom: 16 }}>
          <div className="row" style={{ alignItems: 'flex-start', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <div className="row" style={{ gap: 8, marginBottom: 4 }}>
                <PreloadIcon />
                <span className="h2" style={{ margin: 0 }}>
                  Pre-cached resumes ({preloadInfo.count})
                </span>
              </div>
              <div className="muted" style={{ fontSize: 13 }}>
                {preloadResult
                  ? `Loaded ${preloadResult.loaded} new candidate${preloadResult.loaded === 1 ? '' : 's'}${preloadResult.skipped ? ` · skipped ${preloadResult.skipped} already in role` : ''}.`
                  : 'Skip the upload + embedding step. Inserts candidates with pre-computed chunks straight into the active role.'}
              </div>
            </div>
            <button className="primary" onClick={handleLoadPreloaded} disabled={preloading}>
              {preloading
                ? <><span className="spinner" />&nbsp;Loading…</>
                : preloadResult ? 'Re-load' : `Load ${preloadInfo.count} pre-cached resumes`}
            </button>
            {preloadResult && (
              <button className="primary" onClick={handleContinue}>
                Continue to criteria →
              </button>
            )}
          </div>
        </div>
      )}

      <CVDropZone roleId={roleId} onUploaded={handleUploaded} />

      {!!uploaded.length && (
        <div className="card stack" style={{ marginTop: 16 }}>
          <div className="row">
            <div>
              <div className="h2" style={{ margin: 0 }}>
                {uploaded.length} CV{uploaded.length === 1 ? '' : 's'} uploaded
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                {uploaded.filter((r) => r.status === 'pending').length} ready · {uploaded.filter((r) => r.status === 'error').length} errored
              </div>
            </div>
            <div className="spacer" />
            <button className="primary" onClick={handleContinue}>
              Continue to criteria →
            </button>
          </div>
        </div>
      )}

      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
    </>
  )
}

function PreloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-accent)' }}>
      <path d="M21 12a9 9 0 1 1-3-6.7" />
      <polyline points="21 4 21 10 15 10" />
    </svg>
  )
}

