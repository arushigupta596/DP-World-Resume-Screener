import { useState } from 'react'
import { searchCandidates } from '../lib/api.js'

export default function SearchBar({ roleId, onResults, onClear }) {
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async (e) => {
    e?.preventDefault()
    setError('')
    const q = query.trim()
    if (!q) return
    setBusy(true)
    try {
      const { results } = await searchCandidates(roleId, q, 20)
      onResults?.(results, q)
    } catch (err) {
      setError(err.message || 'Search failed')
    } finally {
      setBusy(false)
    }
  }

  const clear = () => {
    setQuery('')
    setError('')
    onClear?.()
  }

  return (
    <form onSubmit={run} className="card" style={{ marginBottom: 16, padding: '14px 18px' }}>
      <div className="row" style={{ gap: 10 }}>
        <SearchIcon />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search candidates by skill, experience, tools… (hybrid vector + keyword)"
          style={{ flex: 1, border: 'none', padding: '6px 0', background: 'transparent' }}
        />
        {query && (
          <button type="button" onClick={clear} title="Clear">×</button>
        )}
        <button type="submit" className="primary" disabled={busy || !query.trim()}>
          {busy ? <><span className="spinner" />&nbsp;Searching…</> : 'Search'}
        </button>
      </div>
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
    </form>
  )
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-text-secondary)' }}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}
