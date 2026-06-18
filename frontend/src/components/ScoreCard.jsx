export default function ScoreCard({ total, scored, shortlist, review, reject }) {
  const pct = total ? Math.round((scored / total) * 100) : 0

  return (
    <div className="card stack">
      <div className="row" style={{ gap: 16, flexWrap: 'wrap' }}>
        <Metric label="Scored" value={`${scored} / ${total}`} />
        <Metric label="Shortlist" value={shortlist} tone="shortlist" />
        <Metric label="Review" value={review} tone="review" />
        <Metric label="Reject" value={reject} tone="reject" />
      </div>
      <div style={{
        height: 4, background: 'var(--color-border-tertiary)',
        borderRadius: 2, overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: 'var(--color-accent)',
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  )
}

function Metric({ label, value, tone }) {
  const color = tone === 'shortlist' ? 'var(--color-shortlist-fg)'
    : tone === 'review' ? 'var(--color-review-fg)'
    : tone === 'reject' ? 'var(--color-reject-fg)'
    : 'var(--color-text-primary)'
  return (
    <div style={{ flex: 1, minWidth: 100 }}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600, color }}>{value}</div>
    </div>
  )
}
