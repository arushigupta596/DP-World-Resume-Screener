import { useState } from 'react'
import { extractJD } from '../lib/api.js'

const JD_ACCEPT = '.docx,.txt,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain'

export default function JDInput({ onConfirm }) {
  const [stage, setStage] = useState('input') // input | review | confirmed
  const [jdText, setJdText] = useState('')
  const [file, setFile] = useState(null)
  const [parsed, setParsed] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleExtract = async () => {
    setError('')
    if (!jdText.trim() && !file) {
      setError('Paste a job description or upload a .docx / .txt file.')
      return
    }
    setLoading(true)
    try {
      const result = await extractJD({ jdText: jdText.trim() || undefined, file })
      setParsed(result)
      setStage('review')
    } catch (e) {
      setError(e.message || 'Failed to extract JD')
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    const lower = f.name.toLowerCase()
    if (!(lower.endsWith('.docx') || lower.endsWith('.txt'))) {
      setError('Only .docx or .txt files are accepted for the JD.')
      e.target.value = ''
      return
    }
    setError('')
    setFile(f)
  }

  if (stage === 'input') {
    return (
      <div className="card stack-lg">
        <div>
          <div className="h1">Set up the role</div>
          <div className="muted">Paste the job description below or upload a .docx / .txt file. Claude will extract the criteria and weights.</div>
        </div>

        <div className="stack">
          <label className="h2">Job description text</label>
          <textarea
            placeholder="Paste the JD here..."
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={12}
          />
        </div>

        <div className="stack">
          <label className="h2">Or upload a file</label>
          <input type="file" accept={JD_ACCEPT} onChange={handleFileChange} />
          {file && <div className="muted">Selected: {file.name}</div>}
        </div>

        {error && <div className="error">{error}</div>}

        <div className="row">
          <div className="spacer" />
          <button className="primary" onClick={handleExtract} disabled={loading}>
            {loading ? <><span className="spinner" /> &nbsp;Extracting…</> : 'Extract criteria →'}
          </button>
        </div>
      </div>
    )
  }

  if (stage === 'review' && parsed) {
    return <Review parsed={parsed} setParsed={setParsed} onBack={() => setStage('input')} onConfirm={() => { onConfirm(parsed); setStage('confirmed') }} />
  }

  return (
    <div className="card">
      <div className="h2">Role confirmed</div>
      <div className="muted">Continuing to upload step…</div>
    </div>
  )
}

function Review({ parsed, setParsed, onBack, onConfirm }) {
  const weightSum = (parsed.scoring_criteria || []).reduce((s, c) => s + Number(c.weight || 0), 0)
  const weightOk = weightSum === 100

  const updateCriterion = (idx, field, value) => {
    setParsed({
      ...parsed,
      scoring_criteria: parsed.scoring_criteria.map((c, i) =>
        i === idx ? { ...c, [field]: field === 'weight' ? Number(value) : value } : c
      ),
    })
  }

  const updateField = (field, value) => {
    setParsed({ ...parsed, [field]: value })
  }

  return (
    <div className="card stack-lg">
      <div>
        <div className="h1">Review extracted role</div>
        <div className="muted">Adjust anything that's off. Weights must sum to 100.</div>
      </div>

      <div className="stack">
        <label className="h2">Title</label>
        <input type="text" value={parsed.title || ''} onChange={(e) => updateField('title', e.target.value)} />
      </div>
      <div className="row" style={{ gap: 16 }}>
        <div className="stack" style={{ flex: 1 }}>
          <label className="h2">Company</label>
          <input type="text" value={parsed.company || ''} onChange={(e) => updateField('company', e.target.value)} />
        </div>
        <div className="stack" style={{ flex: 1 }}>
          <label className="h2">Location</label>
          <input type="text" value={parsed.location || ''} onChange={(e) => updateField('location', e.target.value)} />
        </div>
      </div>
      <div className="row" style={{ gap: 16 }}>
        <div className="stack" style={{ flex: 1 }}>
          <label className="h2">Reports to</label>
          <input type="text" value={parsed.reports_to || ''} onChange={(e) => updateField('reports_to', e.target.value)} />
        </div>
        <div className="stack" style={{ flex: 1 }}>
          <label className="h2">Min experience (years)</label>
          <input
            type="number"
            value={parsed.min_experience_years ?? 0}
            onChange={(e) => updateField('min_experience_years', Number(e.target.value))}
          />
        </div>
      </div>

      <div className="stack">
        <div className="row">
          <div className="h2">Scoring criteria</div>
          <div className="spacer" />
          <span className={weightOk ? 'badge teal' : 'badge reject'}>
            Total weight: {weightSum}{weightOk ? '' : ' (must = 100)'}
          </span>
        </div>
        {(parsed.scoring_criteria || []).map((c, idx) => (
          <div key={c.id} className="row" style={{ gap: 8 }}>
            <span className="badge teal" style={{ minWidth: 36, justifyContent: 'center' }}>{c.id}</span>
            <input
              type="text"
              value={c.label}
              onChange={(e) => updateCriterion(idx, 'label', e.target.value)}
            />
            <input
              type="number"
              min="0" max="100"
              value={c.weight}
              style={{ width: 96 }}
              onChange={(e) => updateCriterion(idx, 'weight', e.target.value)}
            />
            <span className="muted" style={{ minWidth: 16 }}>%</span>
          </div>
        ))}
      </div>

      <div className="row">
        <button onClick={onBack}>← Back</button>
        <div className="spacer" />
        <button className="primary" onClick={onConfirm} disabled={!weightOk || !parsed.title}>
          Confirm role setup →
        </button>
      </div>
    </div>
  )
}
