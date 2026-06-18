import { useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { triggerScoring } from '../lib/api.js'

const RUBRIC_HINTS = {
  C1: 'Strongest signal: named offshore marine, OSV, subsea, or offshore O&G role. Also strong: ports, shipping, energy, offshore renewables.',
  C2: 'Strongest signal: published market reports, forecasting models, or competitor intelligence work. Trend reporting as part of role also counts.',
  C3: 'Strongest signal: advanced Excel (modelling, VBA, pivots), Power BI dashboards built, strong PowerPoint evidence.',
  C4: 'Strongest signal: explicit examples of analysis leading to commercial wins, revenue growth, or new business.',
  C5: 'Strongest signal: named senior stakeholders (VP/C-level), research directly cited in strategic decisions.',
}

export default function Criteria() {
  const { roleId } = useParams()
  const { activeRole } = useOutletContext() || {}
  const navigate = useNavigate()
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  const criteria = activeRole?.scoring_criteria || []
  const totalWeight = criteria.reduce((s, c) => s + Number(c.weight || 0), 0)

  const handleStartScoring = async () => {
    setError('')
    setStarting(true)
    try {
      await triggerScoring(roleId)
      navigate(`/role/${roleId}/scoring`)
    } catch (e) {
      setError(e.message || 'Failed to start scoring')
      setStarting(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="breadcrumb">CV Screener / Criteria</div>
          <div className="page-title">Scoring criteria & weightage</div>
          {activeRole && (
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {activeRole.title}
              {activeRole.company && <> &middot; {activeRole.company}</>}
            </div>
          )}
        </div>
        <div className="spacer" />
        <div className="step-indicator" style={{ margin: 0 }}>
          <span className="dot" /> Upload
          <span className="dot active" /> Step 2 of 3
          <span className="dot" /> Scoring
        </div>
      </div>

      <div className="card stack" style={{ marginBottom: 16 }}>
        <div className="row">
          <div>
            <div className="h2" style={{ margin: 0 }}>How each CV will be scored</div>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              5 criteria, weights total {totalWeight}%. Each criterion is scored 0-10; the weighted sum becomes the candidate's total out of 100.
            </div>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <div className="badge shortlist">≥ 70 Shortlist</div>
            <div className="badge review">50–69 Review</div>
            <div className="badge reject">&lt; 50 Reject</div>
          </div>
        </div>
      </div>

      <div className="stack">
        {criteria.map((c) => {
          const weight = Number(c.weight || 0)
          return (
            <div key={c.id} className="card criteria-row">
              <div className="row" style={{ alignItems: 'flex-start', gap: 16 }}>
                <div className="criteria-id-chip">{c.id}</div>
                <div style={{ flex: 1 }}>
                  <div className="criteria-label">{c.label}</div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    {RUBRIC_HINTS[c.id] || ''}
                  </div>
                </div>
                <div className="criteria-weight-block">
                  <div className="criteria-weight-num">{Math.round(weight)}%</div>
                  <div className="criteria-weight-bar"><span style={{ width: `${weight}%` }} /></div>
                </div>
              </div>
            </div>
          )
        })}

        {!criteria.length && (
          <div className="card muted">No criteria configured for this role.</div>
        )}
      </div>

      <div className="row" style={{ marginTop: 20 }}>
        <Link to={`/role/${roleId}/upload`}><button>← Back to upload</button></Link>
        <div className="spacer" />
        <button className="primary" onClick={handleStartScoring} disabled={starting || !criteria.length}>
          {starting ? <><span className="spinner" /> &nbsp;Starting…</> : 'Start scoring →'}
        </button>
      </div>

      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
    </>
  )
}
