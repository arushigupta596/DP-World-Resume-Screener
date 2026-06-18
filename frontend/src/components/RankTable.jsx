import { useMemo, useState } from 'react'

const FILTERS = ['All', 'Shortlist', 'Review', 'Reject']
const SORTS = [
  { key: 'score', label: 'Total score' },
  { key: 'name', label: 'Name' },
  { key: 'file', label: 'File' },
]

function scoreColor(total) {
  if (total == null) return 'var(--color-text-secondary)'
  if (total >= 70) return 'var(--color-shortlist-fg)'
  if (total >= 50) return 'var(--color-review-fg)'
  return 'var(--color-reject-fg)'
}

function StatusBadge({ status, recommendation }) {
  if (status === 'scoring') return <span className="badge muted"><span className="spinner" />&nbsp;Scoring</span>
  if (status === 'pending') return <span className="badge muted">Pending</span>
  if (status === 'error') return <span className="badge reject">Error</span>
  if (recommendation === 'Shortlist') return <span className="badge shortlist">Shortlist</span>
  if (recommendation === 'Review') return <span className="badge review">Review</span>
  if (recommendation === 'Reject') return <span className="badge reject">Reject</span>
  return <span className="badge muted">{status}</span>
}

function MiniBar({ score }) {
  const pct = Math.max(0, Math.min(10, Number(score || 0))) * 10
  return (
    <span className="mini-bar" title={score != null ? `${score} / 10` : ''}>
      <span style={{ width: `${pct}%` }} />
    </span>
  )
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

export default function RankTable({ candidates, onSelect }) {
  const [filter, setFilter] = useState('All')
  const [sortKey, setSortKey] = useState('score')

  const filtered = useMemo(() => {
    let rows = candidates
    if (filter !== 'All') {
      rows = rows.filter((c) => (c.score?.recommendation || '') === filter)
    }
    const sorted = [...rows]
    if (sortKey === 'name') {
      sorted.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    } else if (sortKey === 'file') {
      sorted.sort((a, b) => (a.file_name || '').localeCompare(b.file_name || ''))
    } else {
      sorted.sort((a, b) => {
        const av = a.score?.total_score ?? -1
        const bv = b.score?.total_score ?? -1
        return bv - av
      })
    }
    return sorted
  }, [candidates, filter, sortKey])

  return (
    <div className="card stack">
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={filter === f ? 'primary' : ''}
          >
            {f}
          </button>
        ))}
        <div className="spacer" />
        <span className="muted">Sort:</span>
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} style={{ width: 'auto' }}>
          {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>

      <table className="rank">
        <thead>
          <tr>
            <th style={{ width: 40 }}>#</th>
            <th>Name</th>
            <th>File</th>
            <th style={{ width: 100 }}>Score</th>
            <th style={{ width: 110 }}>Status</th>
            <th style={{ width: 240 }}>C1–C5</th>
            <th>Bonus</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((c, idx) => {
            const total = c.score?.total_score
            const criteria = c.score?.criteria_scores || {}
            const bonus = c.score?.bonus_tools || []
            return (
              <tr key={c.id} onClick={() => onSelect?.(c.id)}>
                <td>{idx + 1}</td>
                <td>{c.name || <span className="muted">Unknown</span>}</td>
                <td>{truncate(c.file_name, 25)}</td>
                <td style={{ fontWeight: 600, fontSize: 16, color: scoreColor(total) }}>
                  {total != null ? total.toFixed(1) : '—'}
                </td>
                <td><StatusBadge status={c.status} recommendation={c.score?.recommendation} /></td>
                <td>
                  <div className="row" style={{ gap: 4 }}>
                    {['C1', 'C2', 'C3', 'C4', 'C5'].map((cid) => (
                      <MiniBar key={cid} score={criteria[cid]?.score} />
                    ))}
                  </div>
                </td>
                <td>
                  {bonus.length > 0 && <span className="badge teal">{bonus.length} tool{bonus.length === 1 ? '' : 's'}</span>}
                </td>
              </tr>
            )
          })}
          {!filtered.length && (
            <tr><td colSpan={7} className="muted" style={{ textAlign: 'center', padding: 32 }}>No candidates match this filter.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
