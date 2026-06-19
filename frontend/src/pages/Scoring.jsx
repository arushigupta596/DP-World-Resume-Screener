import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import RankTable from '../components/RankTable.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import SearchBar from '../components/SearchBar.jsx'
import {
  getCandidates, getExportUrl, getScoringStatus, scoreOne, triggerScoring,
} from '../lib/api.js'

const CONCURRENCY = 3

export default function Scoring() {
  const { roleId } = useParams()
  const { activeRole } = useOutletContext() || {}
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState([])
  const [status, setStatus] = useState({ total: 0, pending: 0, scoring: 0, scored: 0, error: 0 })
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const [searchResults, setSearchResults] = useState(null)  // null = no search active
  const [searchQuery, setSearchQuery] = useState('')
  const cancelRef = useRef(false)

  useEffect(() => {
    refresh().then(() => {
      // Auto-start the scoring loop on mount if there's work to do.
      // The Criteria page triggers scoring before navigating here.
      runScoringLoop()
    })
    return () => { cancelRef.current = true }
  }, [roleId])

  const refresh = async () => {
    try {
      const [statusResp, candsResp] = await Promise.all([
        getScoringStatus(roleId),
        getCandidates(roleId),
      ])
      setStatus(statusResp)
      setCandidates(candsResp.candidates || [])
      return { statusResp, candsResp }
    } catch (e) {
      setError(e.message)
      return null
    }
  }

  const runScoringLoop = async () => {
    if (running) return
    setRunning(true)
    cancelRef.current = false

    try {
      const { pending } = await triggerScoring(roleId)
      if (!pending?.length) {
        setRunning(false)
        return
      }

      let cursor = 0
      const next = () => {
        if (cursor >= pending.length || cancelRef.current) return null
        const id = pending[cursor++]
        return id
      }

      const worker = async () => {
        while (true) {
          const id = next()
          if (!id) return
          try {
            await scoreOne(id)
          } catch (e) {
            // score_candidate already records the error on the candidate row;
            // surface a soft toast and keep going.
            console.warn(`scoring ${id} failed:`, e.message)
          }
          await refresh()
        }
      }

      await Promise.all(Array.from({ length: CONCURRENCY }, worker))
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
      refresh()
    }
  }

  const handleExport = () => {
    window.location.href = getExportUrl(roleId)
  }

  const handleRescore = () => runScoringLoop()

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
        {running && (
          <span className="muted" style={{ fontSize: 13 }}>
            <span className="spinner" />&nbsp;Scoring in progress — keep this tab open
          </span>
        )}
        <div className="spacer" />
        <Link to={`/role/${roleId}/report`}><button>Open HR report</button></Link>
        <button onClick={handleExport}>Export to Excel</button>
        {(status.error > 0 || (!running && status.pending > 0)) && (
          <button className="primary" onClick={handleRescore} disabled={running}>
            Re-score {status.pending + status.error} pending/failed
          </button>
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
        <SearchBar
          roleId={roleId}
          onResults={(results, q) => { setSearchResults(results); setSearchQuery(q) }}
          onClear={() => { setSearchResults(null); setSearchQuery('') }}
        />

        {searchResults ? (
          <SearchResults
            results={searchResults}
            query={searchQuery}
            onSelect={(cid) => navigate(`/role/${roleId}/candidate/${cid}`)}
            onClear={() => { setSearchResults(null); setSearchQuery('') }}
          />
        ) : (
          <RankTable
            candidates={candidates}
            onSelect={(cid) => navigate(`/role/${roleId}/candidate/${cid}`)}
          />
        )}
      </div>

      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
    </>
  )
}

function SearchResults({ results, query, onSelect, onClear }) {
  return (
    <div className="card stack">
      <div className="row">
        <div>
          <div className="h2" style={{ margin: 0 }}>
            {results.length} match{results.length === 1 ? '' : 'es'} for "{query}"
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Ranked by hybrid score (vector + keyword)
          </div>
        </div>
        <div className="spacer" />
        <button onClick={onClear}>Clear search</button>
      </div>

      {results.length === 0 && (
        <div className="muted" style={{ padding: 16, textAlign: 'center' }}>
          No candidates matched this query. Try different keywords.
        </div>
      )}

      <div className="stack">
        {results.map((r) => (
          <div
            key={r.candidate_id}
            className="search-result-row"
            onClick={() => onSelect?.(r.candidate_id)}
          >
            <div className="row" style={{ alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div className="row" style={{ gap: 8, marginBottom: 4 }}>
                  <strong>{r.name || 'Unknown candidate'}</strong>
                  <span className="muted" style={{ fontSize: 12 }}>{r.file_name}</span>
                  {r.score?.recommendation && (
                    <span className={`badge ${r.score.recommendation.toLowerCase()}`}>
                      {r.score.recommendation}
                    </span>
                  )}
                </div>
                <div className="muted search-snippet">
                  {r.matched_chunk}
                </div>
              </div>
              <div style={{ minWidth: 90, textAlign: 'right' }}>
                {r.score?.total_score != null && (
                  <div style={{ fontWeight: 700, fontSize: 18 }}>
                    {Number(r.score.total_score).toFixed(1)}
                  </div>
                )}
                <div className="muted" style={{ fontSize: 11 }}>
                  match {(r.rrf_score * 100).toFixed(1)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
