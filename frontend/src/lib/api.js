// API base resolution:
//   - Explicit VITE_API_BASE env var wins (set to http://localhost:8000 in
//     local dev, set in Vercel project settings for prod overrides).
//   - In production builds without an env var, default to /_/backend so the
//     experimentalServices routing reaches the FastAPI service.
//   - In dev without an env var, fall back to empty (same-origin).
const _envBase = import.meta.env.VITE_API_BASE
const BASE =
  _envBase !== undefined && _envBase !== ''
    ? _envBase
    : import.meta.env.PROD ? '/_/backend' : ''

async function handle(res) {
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    const err = new Error(body || `${res.status} ${res.statusText}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function createRole(roleData) {
  const res = await fetch(`${BASE}/api/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(roleData),
  })
  return handle(res)
}

export async function getRole(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}`)
  return handle(res)
}

export async function getActiveRole() {
  const res = await fetch(`${BASE}/api/active-role`)
  return handle(res)
}

export async function extractJD({ jdText, file }) {
  const form = new FormData()
  if (jdText) form.append('jd_text', jdText)
  if (file) form.append('file', file)
  const res = await fetch(`${BASE}/api/extract-jd`, { method: 'POST', body: form })
  return handle(res)
}

export async function uploadOne(roleId, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates/single`, {
    method: 'POST',
    body: form,
  })
  return handle(res)
}

export async function clearCandidates(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates`, { method: 'DELETE' })
  return handle(res)
}

export async function getCandidates(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates`)
  return handle(res)
}

export async function triggerScoring(roleId) {
  // Backend returns the list of candidate ids that still need scoring.
  const res = await fetch(`${BASE}/api/roles/${roleId}/score`, { method: 'POST' })
  return handle(res)
}

export async function scoreOne(candidateId) {
  const res = await fetch(`${BASE}/api/candidates/${candidateId}/score`, { method: 'POST' })
  return handle(res)
}

export async function getScoringStatus(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/score/status`)
  return handle(res)
}

export async function getCandidate(candidateId) {
  const res = await fetch(`${BASE}/api/candidates/${candidateId}`)
  return handle(res)
}

export function getExportUrl(roleId) {
  return `${BASE}/api/roles/${roleId}/export`
}

export async function getPreloadedInfo() {
  const res = await fetch(`${BASE}/api/preloaded-resumes/info`)
  return handle(res)
}

export async function loadPreloaded(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/load-preloaded`, { method: 'POST' })
  return handle(res)
}

export async function searchCandidates(roleId, query, limit = 20) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  })
  return handle(res)
}
