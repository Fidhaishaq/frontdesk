import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getStats, getErrorMessage } from '../services/api'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setError(null)
      const data = await getStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
      setError(getErrorMessage(err, 'Failed to load statistics from server'))
    } finally {
      setLoading(false)
    }
  }

  const goToTickets = (filter = {}) => {
    const params = new URLSearchParams(filter).toString()
    navigate(`/tickets${params ? `?${params}` : ''}`)
  }

  if (loading) {
    return <div className="spinner-container"><div className="spinner"></div></div>
  }

  const statCards = [
    { label: 'Total Tickets', value: stats?.total_tickets || 0, icon: '🎫', color: 'blue', onClick: () => goToTickets() },
    { label: 'Open', value: stats?.open_tickets || 0, icon: '📂', color: 'green', onClick: () => goToTickets({ status: 'open' }) },
    { label: 'In Progress', value: stats?.in_progress_tickets || 0, icon: '⚡', color: 'blue', onClick: () => goToTickets({ status: 'in_progress' }) },
    { label: 'Waiting', value: stats?.waiting_tickets || 0, icon: '⏳', color: 'orange', onClick: () => goToTickets({ status: 'waiting_for_customer' }) },
    { label: 'Resolved', value: stats?.resolved_tickets || 0, icon: '✅', color: 'green', onClick: () => goToTickets({ status: 'resolved' }) },
    { label: 'Overdue', value: stats?.overdue_tickets || 0, icon: '🔥', color: 'red', highlighted: (stats?.overdue_tickets || 0) > 0, onClick: () => goToTickets({ overdue: 'true' }) },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back, {user?.name}</p>
        </div>
      </div>

      {error && (
        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: '#991b1b',
          fontSize: '0.875rem'
        }}>
          <div>
            <strong>Notice:</strong> {error}
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadStats}
            style={{ marginLeft: '12px' }}
          >
            Retry
          </button>
        </div>
      )}

      <div className="stats-grid">
        {statCards.map((card) => (
          <div
            key={card.label}
            className={`stat-card ${card.highlighted ? 'highlighted' : ''}`}
            onClick={card.onClick}
          >
            <div className={`stat-icon ${card.color}`}>{card.icon}</div>
            <div className="stat-info">
              <div className="stat-value">{card.value}</div>
              <div className="stat-label">{card.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Priority Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Priority Distribution</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {['urgent', 'medium', 'small'].map(priority => {
              const count = stats?.tickets_by_priority?.[priority] || 0
              const total = stats?.total_tickets || 1
              const pct = Math.round((count / total) * 100) || 0
              const colors = { urgent: '#ef4444', medium: '#f59e0b', small: '#3b82f6' }
              return (
                <div key={priority}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ textTransform: 'capitalize', fontWeight: 500, fontSize: '0.875rem' }}>{priority}</span>
                    <span style={{ color: '#64748b', fontSize: '0.8125rem' }}>{count} ({pct}%)</span>
                  </div>
                  <div style={{ height: '8px', background: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: colors[priority], borderRadius: '4px', transition: 'width 0.5s ease' }}></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Tickets</h3>
          </div>
          {stats?.recent_tickets?.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {stats.recent_tickets.slice(0, 8).map(ticket => (
                <div
                  key={ticket.id}
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '8px 12px', borderRadius: '8px', cursor: 'pointer',
                    border: '1px solid #f1f5f9', transition: 'background 0.15s'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}
                >
                  <div>
                    <span style={{ fontFamily: 'monospace', color: '#3b82f6', fontWeight: 600, fontSize: '0.8125rem', marginRight: '8px' }}>
                      {ticket.ticket_number}
                    </span>
                    <span style={{ fontSize: '0.875rem' }}>{ticket.subject}</span>
                  </div>
                  <span className={`badge badge-${ticket.priority}`}>{ticket.priority}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-center" style={{ padding: '20px' }}>No tickets yet</p>
          )}
        </div>
      </div>
    </div>
  )
}
