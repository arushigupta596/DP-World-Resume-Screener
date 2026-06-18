import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCandidates, getRole } from '../lib/api.js'

const REPORT_STYLES = `
  @media print {
    body { background: white !important; }
    .shell { display: block !important; }
    .shell-sidebar, .shell-context { display: none !important; }
    .shell-main { padding: 0 !important; background: white !important; }
    .no-print { display: none !important; }
    .report-block { page-break-inside: avoid; }
    @page { size: A4; margin: 18mm 14mm; }
  }
`

export default function Report() {
  const { roleId } = useParams()
  const [role, setRole] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getRole(roleId), getCandidates(roleId)])
      .then(([r, c]) => { setRole(r); setCandidates(c.candidates || []) })
      .catch((e) => setError(e.message))
  }, [roleId])

  const stats = useMemo(() => {
    const scored = candidates.filter((c) => c.score?.total_score != null)
    const totals = scored.map((c) => c.score.total_score)
    const sum = totals.reduce((a, b) => a + b, 0)
    return {
      total: candidates.length,
      scored: scored.length,
      shortlist: scored.filter((c) => c.score.recommendation === 'Shortlist').length,
      review: scored.filter((c) => c.score.recommendation === 'Review').length,
      reject: scored.filter((c) => c.score.recommendation === 'Reject').length,
      error: candidates.filter((c) => c.status === 'error').length,
      avgScore: scored.length ? (sum / scored.length).toFixed(1) : '—',
      ranked: [...scored].sort((a, b) => b.score.total_score - a.score.total_score),
    }
  }, [candidates])

  const shortlisted = stats.ranked?.filter((c) => c.score.recommendation === 'Shortlist') || []
  const top10 = stats.ranked?.slice(0, 10) || []

  if (error) return <div className="error">{error}</div>

  return (
    <>
      <style>{REPORT_STYLES}</style>

      <div className="row no-print" style={{ marginBottom: 16 }}>
        <Link to={`/role/${roleId}/scoring`}>← Back to ranking</Link>
        <div className="spacer" />
        <button className="primary" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>

      <div className="card report-block">
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 1 }}>
          HR Screening Report
        </div>
        <div className="h1" style={{ fontSize: 26, marginTop: 8 }}>{role?.title || '—'}</div>
        <div className="muted">
          {role?.company && <>{role.company} &middot; </>}
          {role?.location && <>{role.location} &middot; </>}
          Reports to {role?.reports_to || '—'}
        </div>
        <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          Generated {new Date().toLocaleString()}
        </div>
      </div>

      <div className="card report-block" style={{ marginTop: 16 }}>
        <div className="h2">Summary</div>
        <div className="row" style={{ gap: 24, marginTop: 12, flexWrap: 'wrap' }}>
          <Metric label="Candidates" value={stats.total} />
          <Metric label="Scored" value={stats.scored} />
          <Metric label="Shortlist" value={stats.shortlist} tone="shortlist" />
          <Metric label="Review" value={stats.review} tone="review" />
          <Metric label="Reject" value={stats.reject} tone="reject" />
          <Metric label="Errors" value={stats.error} />
          <Metric label="Avg score" value={stats.avgScore} />
        </div>
      </div>

      <div className="card report-block" style={{ marginTop: 16 }}>
        <div className="h2">Top 10 ranked</div>
        <table className="rank" style={{ marginTop: 8 }}>
          <thead>
            <tr>
              <th style={{ width: 40 }}>#</th>
              <th>Name</th>
              <th style={{ width: 80 }}>Score</th>
              <th style={{ width: 110 }}>Recommendation</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {top10.map((c, idx) => (
              <tr key={c.id} style={{ cursor: 'default' }}>
                <td>{idx + 1}</td>
                <td>{c.name || '—'}</td>
                <td><strong>{c.score.total_score.toFixed(1)}</strong></td>
                <td>
                  <span className={`badge ${c.score.recommendation?.toLowerCase()}`}>
                    {c.score.recommendation}
                  </span>
                </td>
                <td style={{ fontSize: 12 }}>{c.score.ai_summary}</td>
              </tr>
            ))}
            {!top10.length && (
              <tr><td colSpan={5} className="muted" style={{ textAlign: 'center', padding: 24 }}>No scored candidates yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {shortlisted.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div className="h2" style={{ margin: '0 4px 12px' }}>Shortlist briefs</div>
          {shortlisted.map((c) => (
            <div key={c.id} className="card report-block" style={{ marginBottom: 12 }}>
              <div className="row">
                <div>
                  <div className="h2" style={{ marginBottom: 2 }}>{c.name || '—'}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{c.file_name}</div>
                </div>
                <div className="spacer" />
                <span className="badge shortlist">Shortlist</span>
                <strong style={{ fontSize: 18, marginLeft: 12 }}>{c.score.total_score.toFixed(1)} / 100</strong>
              </div>
              <div style={{ marginTop: 10, fontSize: 13 }}>{c.score.ai_summary}</div>

              <div className="row" style={{ gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
                {Object.entries(c.score.criteria_scores || {}).map(([cid, entry]) => (
                  <div key={cid} style={{ fontSize: 12, minWidth: 160 }}>
                    <strong>{cid}:</strong> {entry.score}/10 &middot; <span className="muted">{entry.evidence}</span>
                  </div>
                ))}
              </div>

              {!!(c.score.bonus_tools?.length) && (
                <div className="row" style={{ flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                  {c.score.bonus_tools.map((t, i) => <span key={i} className="badge teal">{t}</span>)}
                </div>
              )}
              {!!(c.score.risk_flags?.length) && (
                <div className="row" style={{ flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                  {c.score.risk_flags.map((f, i) => <span key={i} className="tag-pill">{f}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function Metric({ label, value, tone }) {
  const color = tone === 'shortlist' ? 'var(--color-shortlist-fg)'
    : tone === 'review' ? 'var(--color-review-fg)'
    : tone === 'reject' ? 'var(--color-reject-fg)'
    : 'var(--color-text-primary)'
  return (
    <div style={{ minWidth: 90 }}>
      <div className="muted" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600, color }}>{value}</div>
    </div>
  )
}
