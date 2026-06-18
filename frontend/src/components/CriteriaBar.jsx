import { useState } from 'react'

function confidenceColor(level) {
  if (level === 'high') return 'var(--color-confidence-high)'
  if (level === 'medium') return 'var(--color-confidence-medium)'
  if (level === 'low') return 'var(--color-confidence-low)'
  return 'var(--color-border-secondary)'
}

export default function CriteriaBar({ criteria, scores }) {
  const [open, setOpen] = useState({})

  if (!criteria || !criteria.length) return null

  return (
    <div className="stack">
      {criteria.map((c) => {
        const entry = (scores && scores[c.id]) || {}
        const score = Number(entry.score ?? 0)
        const pct = Math.max(0, Math.min(10, score)) * 10
        const evidence = entry.evidence || 'Not mentioned'
        const confidence = entry.confidence || 'low'
        const expanded = !!open[c.id]

        return (
          <div
            key={c.id}
            className="card"
            style={{ padding: '14px 18px', cursor: 'pointer' }}
            onClick={() => setOpen({ ...open, [c.id]: !expanded })}
          >
            <div className="row" style={{ gap: 12 }}>
              <span className="badge teal" style={{ minWidth: 36, justifyContent: 'center' }}>{c.id}</span>
              <span style={{ flex: 1, fontWeight: 500 }}>{c.label}</span>
              <span
                title={`Confidence: ${confidence}`}
                style={{
                  width: 8, height: 8, borderRadius: 50,
                  background: confidenceColor(confidence),
                }}
              />
              <span style={{ minWidth: 60, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                <strong>{score}</strong> <span className="muted">/ 10</span>
              </span>
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{
                width: '100%', height: 6, background: 'var(--color-border-tertiary)',
                borderRadius: 3, overflow: 'hidden'
              }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-accent)' }} />
              </div>
            </div>
            {expanded && (
              <div style={{ marginTop: 12, fontSize: 13 }} className="muted">
                <strong style={{ color: 'var(--color-text-primary)' }}>Evidence:</strong> {evidence}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
