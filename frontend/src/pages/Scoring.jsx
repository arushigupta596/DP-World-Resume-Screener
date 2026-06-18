import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import RankTable from '../components/RankTable.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import {
  getCandidates, getExportUrl, getScoringStatus, triggerScoring,
} from '../lib/api.js'

export default function Scoring() {
  const { roleId } = useParams()
  const { activeRole } = useOutletContext() || {}
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState([])
  const [status, setStatus] = useState({ total: 0, pending: 0, scoring: 0, scored: 0, error: 0 })
  const [error, setError] = useState('')
  const pollRef = useRef(null)

  useEffect(() => {
    refresh()
    return () => clearInterval(pollRef.current)
  }, [roleId])

  const refresh = async () => {
    try {
      const [statusResp, candsResp] = await Promise.all([
        getScoringStatus(roleId),
        getCandidates(roleId),
      ])
      setStatus(statusResp)
      setCandidates(candsResp.candidates || [])
      if (statusResp.pending + statusResp.scoring === 0) {
        clearInterval(pollRef.current)
        pollRef.current = null
      } else if (!pollRef.current) {
        pollRef.current = setInterval(refresh, 3000)
      }
    } catch (e) {
      setError(e.message)
    }
  }

  const handleExport = () => {
    window.location.href = getExportUrl(roleId)
  }

  const handleRescore = async () => {
    try {
      await triggerScoring(roleId)
      refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  const shortlist = candidates.filter((c) => c.score?.recommendation === 'Shortlist').length
  const review = candidates.filter((c) => c.score?.recommendation === 'Review').length
  const reject = candidates.filter((c) => c.score?.recommendation === 'Reject').length

  return (
    <>
      <div className="page-header">
        <div>
          <div className="breadcrumb">CV Screener / Scoring</div>
          <div className="page-title">Scoring & ranking</div>
          {activeRole && (
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {activeRole.title}
              {activeRole.company && <> &middot; {activeRole.company}</>}
              {activeRole.location && <> &middot; {activeRole.location}</>}
            </div>
          )}
        </div>
        <div className="spacer" />
        <div className="step-indicator" style={{ margin: 0 }}>
          <span className="dot" /> Upload
          <span className="dot" /> Criteria
          <span className="dot active" /> Step 3 of 3
        </div>
      </div>

      <div className="row" style={{ marginBottom: 16, gap: 8 }}>
        <div className="spacer" />
        <Link to={`/role/${roleId}/report`}><button>Open HR report</button></Link>
        <button onClick={handleExport}>Export to Excel</button>
        {status.error > 0 && (
          <button className="primary" onClick={handleRescore}>Re-score failed ({status.error})</button>
        )}
      </div>

      <ScoreCard
        total={status.total}
        scored={status.scored}
        shortlist={shortlist}
        review={review}
        reject={reject}
      />

      <div style={{ marginTop: 16 }}>
        <RankTable
          candidates={candidates}
          onSelect={(cid) => navigate(`/role/${roleId}/candidate/${cid}`)}
        />
      </div>

      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
    </>
  )
}
