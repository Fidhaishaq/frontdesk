import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Sidebar() {
  const { user, logout, isAdmin } = useAuth()

  const navItems = [
    { to: '/', icon: '📊', label: 'Dashboard' },
    { to: '/tickets', icon: '🎫', label: 'Tickets' },
  ]

  if (isAdmin) {
    navItems.push(
      { to: '/agents', icon: '👥', label: 'Agents' },
      { to: '/audit', icon: '📋', label: 'Audit History' },
      { to: '/holidays', icon: '📅', label: 'Holidays' },
    )
  }

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>Frontdesk</h1>
        <p>Arvo Systems</p>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? 'active' : ''}`
            }
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-user-avatar">{initials}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">{user?.name}</div>
          <div className="sidebar-user-role">{user?.role}</div>
        </div>
        <button className="sidebar-logout-btn" onClick={logout} title="Logout">
          ⏻
        </button>
      </div>
    </aside>
  )
}
