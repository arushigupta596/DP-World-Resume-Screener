import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import CriteriaBar from '../components/CriteriaBar.jsx'
import { getCandidate } from '../lib/api.js'

export default function CandidateDetail() {
  const { roleId, candidateId } = useParams()
  const [data, setData] = useState(null)
  const [showCV, setShowCV] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getCandidate(candidateId).then(setData).catch((e) => setError(e.message))
  }, [candidateId])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div><span className="spinner" />&nbsp;Loading…</div>

  const { candidate, score, role } = data
  const rec = score?.recommendation
  const total = score?.total_score
  const recClass = rec === 'Shortlist' ? 'shortlist' : rec === 'Review' ? 'review' : rec === 'Reject' ? 'reject' : 'muted'

  return (
    <>
      <div className="page-header">
        <Link to={`/role/${roleId}/scoring`}>← Back to ranking</Link>
        <div className="spacer" />
      </div>

      <div className="card stack" style={{ marginTop: 16 }}>
        <div className="row">
          <div>
            <div className="h1">{candidate.name || 'Unknown candidate'}</div>
            <div className="muted">{candidate.file_name}</div>
          </div>
          <div className="spacer" />
          {rec && <span className={`badge ${recClass}`}>{rec}</span>}
          {total != null && (
            <div style={{ fontSize: 32, fontWeight: 600, marginLeft: 12 }}>
              {Number(total).toFixed(1)}<span className="muted" style={{ fontSize: 14 }}> / 100</span>
            </div>
          )}
        </div>

        {score?.ai_summary && (
          <div className="card" style={{
            background: 'var(--color-accent-soft)',
            borderColor: 'var(--color-accent)',
            padding: '14px 18px',
          }}>
            <div className="h2" style={{ color: 'var(--color-accent)' }}>AI summary</div>
            <div>{score.ai_summary}</div>
          </div>
        )}
      </div>

      {role && score && (
        <div style={{ marginTop: 16 }}>
          <div className="h2" style={{ margin: '0 4px 12px' }}>Criteria breakdown</div>
          <CriteriaBar criteria={role.scoring_criteria || []} scores={score.criteria_scores || {}} />
        </div>
      )}

      {!!(score?.risk_flags?.length) && (
        <div className="card stack" style={{ marginTop: 16 }}>
          <div className="h2">Risk flags</div>
          <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>
            {score.risk_flags.map((f, i) => (
              <span key={i} className="badge reject">{f}</span>
            ))}
          </div>
        </div>
      )}

      {!!(score?.bonus_tools?.length) && (
        <div className="card stack" style={{ marginTop: 16 }}>
          <div className="h2">Bonus tools detected</div>
          <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>
            {score.bonus_tools.map((t, i) => (
              <span key={i} className="badge teal">{t}</span>
            ))}
          </div>
        </div>
      )}

      {candidate.error_msg && (
        <div className="error" style={{ marginTop: 16 }}>{candidate.error_msg}</div>
      )}

      <div className="card stack" style={{ marginTop: 16 }}>
        <div className="row">
          <div className="h2">Raw CV text</div>
          <div className="spacer" />
          <button onClick={() => setShowCV(!showCV)}>{showCV ? 'Hide' : 'Show'}</button>
        </div>
        {showCV && (
          <pre style={{
            whiteSpace: 'pre-wrap',
            fontSize: 12,
            background: 'var(--color-background-secondary)',
            padding: 12,
            borderRadius: 8,
            maxHeight: 400,
            overflow: 'auto',
          }}>
            {candidate.cv_text || '(no text extracted)'}
          </pre>
        )}
      </div>
    </>
  )
}
