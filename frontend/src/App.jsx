import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell.jsx'
import UploadCVs from './pages/UploadCVs.jsx'
import Criteria from './pages/Criteria.jsx'
import Scoring from './pages/Scoring.jsx'
import CandidateDetail from './pages/CandidateDetail.jsx'
import Report from './pages/Report.jsx'
import { getActiveRole } from './lib/api.js'

export default function App() {
  const [activeRole, setActiveRole] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const fetchRole = () =>
      getActiveRole()
        .then((r) => { if (!cancelled) setActiveRole(r) })
        .catch((e) => {
          if (cancelled) return
          if (e.status === 503) {
            setTimeout(fetchRole, 1500)
          } else {
            setError(e.message || 'Failed to load active role')
          }
        })
    fetchRole()
    return () => { cancelled = true }
  }, [])

  if (error) {
    return (
      <div className="layout">
        <div className="error">{error}</div>
        <div className="muted" style={{ marginTop: 8 }}>
          Check the backend is running and that JD.docx is present in backend/data/.
        </div>
      </div>
    )
  }

  if (!activeRole) {
    return (
      <div className="splash">
        <div className="row">
          <span className="spinner" />&nbsp;<span className="muted">Loading role…</span>
        </div>
      </div>
    )
  }

  const roleId = activeRole.id

  return (
    <Routes>
      <Route path="/" element={<Navigate to={`/role/${roleId}/upload`} replace />} />
      <Route path="/setup" element={<Navigate to={`/role/${roleId}/upload`} replace />} />
      <Route element={<Shell activeRole={activeRole} />}>
        <Route path="/role/:roleId/upload" element={<UploadCVs />} />
        <Route path="/role/:roleId/criteria" element={<Criteria />} />
        <Route path="/role/:roleId/scoring" element={<Scoring />} />
        <Route path="/role/:roleId/candidate/:candidateId" element={<CandidateDetail />} />
        <Route path="/role/:roleId/report" element={<Report />} />
      </Route>
      <Route path="*" element={<Navigate to={`/role/${roleId}/upload`} replace />} />
    </Routes>
  )
}
