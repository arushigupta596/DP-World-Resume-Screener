import { useState } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'

const NAV_ITEMS = [
  { key: 'upload', label: 'Upload CVs', icon: UploadIcon, path: 'upload' },
  { key: 'criteria', label: 'Criteria & Weightage', icon: ScaleIcon, path: 'criteria' },
  { key: 'scoring', label: 'Scoring & Ranking', icon: ChartIcon, path: 'scoring' },
  { key: 'report', label: 'HR Report', icon: DocIcon, path: 'report' },
]

const COLLAPSE_KEY = 'dpw_sidebar_collapsed'

export default function Shell({ activeRole }) {
  const { roleId: routeRoleId } = useParams()
  const roleId = routeRoleId || activeRole?.id

  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === '1'
  )

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0')
      return next
    })
  }

  const handleSidebarBgClick = (e) => {
    // Toggle only when the click lands on the aside background, not on
    // a child (link, image, button, etc.).
    if (e.target === e.currentTarget) toggle()
  }

  return (
    <div className={'shell' + (collapsed ? ' is-collapsed' : '')}>
      <aside
        className="shell-sidebar"
        onClick={handleSidebarBgClick}
        title={collapsed ? 'Click empty area to expand' : 'Click empty area to collapse'}
      >
        <div className="shell-brand">
          <div className="shell-brand-logos">
            <img src="/dpworld-logo.png" alt="DP World" className="shell-brand-logo dpw" />
            <span className="shell-brand-x" aria-hidden="true">×</span>
            <img src="/emb-logo.png" alt="EMB Global" className="shell-brand-logo emb" />
          </div>
          <div className="shell-brand-subtitle">CV Screener</div>
        </div>

        <div className="shell-profile">
          <div className="shell-avatar">HR</div>
          <div className="shell-profile-text">
            <div className="muted" style={{ fontSize: 11 }}>Welcome back,</div>
            <div style={{ fontWeight: 600 }}>Recruiter</div>
          </div>
        </div>

        <nav className="shell-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.key}
              to={`/role/${roleId}/${item.path}`}
              title={item.label}
              className={({ isActive }) => 'shell-nav-item' + (isActive ? ' is-active' : '')}
            >
              <item.icon />
              <span className="shell-nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="shell-sidebar-footer muted">
          <div>Active role pinned</div>
          <div style={{ fontSize: 11, marginTop: 4 }}>JD: data/JD.docx</div>
        </div>
      </aside>

      <main className="shell-main">
        <Outlet context={{ activeRole }} />
      </main>
    </div>
  )
}

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}
function ChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  )
}
function ScaleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v18" />
      <path d="M6 8l-3 6a4 4 0 0 0 6 0z" />
      <path d="M18 8l-3 6a4 4 0 0 0 6 0z" />
      <path d="M4 21h16" />
      <path d="M6 8l6-3 6 3" />
    </svg>
  )
}
function DocIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="14" y2="17" />
    </svg>
  )
}
