import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import JDInput from '../components/JDInput.jsx'
import { createRole } from '../lib/api.js'

export default function SetupRole() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async (parsedJD) => {
    setError('')
    setLoading(true)
    try {
      const payload = {
        title: parsedJD.title,
        company: parsedJD.company || null,
        location: parsedJD.location || null,
        reports_to: parsedJD.reports_to || null,
        min_experience_years: parsedJD.min_experience_years ?? 0,
        min_qualification: parsedJD.min_qualification || null,
        jd_text: parsedJD.jd_text || '',
        scoring_criteria: parsedJD.scoring_criteria || [],
      }
      const role = await createRole(payload)
      localStorage.setItem('dpw_active_role', role.id)
      navigate(`/role/${role.id}/upload`)
    } catch (e) {
      setError(e.message || 'Failed to create role')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      <div className="step-indicator">
        <span className="dot active" /> Step 1 of 3 — Set up role
        <span className="dot" /> Upload CVs
        <span className="dot" /> Scoring
      </div>
      <JDInput onConfirm={handleConfirm} />
      {loading && (
        <div className="row" style={{ marginTop: 16 }}>
          <span className="spinner" />&nbsp;<span className="muted">Saving role…</span>
        </div>
      )}
      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
    </div>
  )
}
