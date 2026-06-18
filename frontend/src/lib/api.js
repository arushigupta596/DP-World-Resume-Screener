const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

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

export async function clearCandidates(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates`, { method: 'DELETE' })
  return handle(res)
}

export async function uploadCVs(roleId, files) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates`, {
    method: 'POST',
    body: form,
  })
  return handle(res)
}

export async function uploadCVsStream(roleId, files, onEvent) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates/stream`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok || !res.body) {
    const body = await res.text().catch(() => '')
    throw new Error(body || `${res.status} ${res.statusText}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const json = line.slice(5).trim()
      if (!json) continue
      try {
        onEvent(JSON.parse(json))
      } catch {
        // ignore malformed chunk; backend always sends valid JSON
      }
    }
  }
}

export async function getCandidates(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/candidates`)
  return handle(res)
}

export async function triggerScoring(roleId) {
  const res = await fetch(`${BASE}/api/roles/${roleId}/score`, { method: 'POST' })
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
