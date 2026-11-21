import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAuditLogs } from '../services/api'
import { useToast } from '../components/Toast'

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

export default function AuditHistory() {
  const navigate = useNavigate()
  const toast = useToast()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ ticket_id: '', action: 'all' })

  useEffect(() => { loadLogs() }, [filters])

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await getAuditLogs(filters)
      setLogs(data.audit_logs || [])
    } catch (err) {
      toast.error('Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  const actionTypes = [
    'ticket_created', 'ticket_claimed', 'ticket_assigned',
    'status_changed', 'priority_changed',
    'customer_reply_sent', 'internal_note_added',
    'ticket_resolved', 'ticket_reopened', 'ticket_auto_closed'
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit History</h1>
          <p className="page-subtitle">Complete activity log across all tickets</p>
        </div>
      </div>

      <div className="filters-bar">
        <input
          className="form-input"
          type="text"
          placeholder="🔍 Filter by Ticket ID (e.g. INC-0001)..."
          value={filters.ticket_id}
          onChange={e => setFilters(f => ({ ...f, ticket_id: e.target.value }))}
          style={{ minWidth: '220px' }}
        />
        <select className="form-select" value={filters.action} onChange={e => setFilters(f => ({ ...f, action: e.target.value }))}>
          <option value="all">All Actions</option>
          {actionTypes.map(a => (
            <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="spinner-container"><div className="spinner"></div></div>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">No audit logs found</div>
          <p className="empty-state-text">Activity will appear here as tickets are created and updated.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Ticket</th>
                <th>Action</th>
                <th>Previous Value</th>
                <th>New Value</th>
                <th>User</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td className="text-muted" style={{ whiteSpace: 'nowrap', fontSize: '0.8125rem' }}>{formatDate(log.created_at)}</td>
                  <td>
                    <span
                      className="ticket-id"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/tickets/${log.ticket_id}`)}
                    >
                      {log.ticket_number || `#${log.ticket_id}`}
                    </span>
                  </td>
                  <td>
                    <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                      {log.action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="text-muted">{log.old_value || '—'}</td>
                  <td className="text-muted">{log.new_value || '—'}</td>
                  <td>{log.user_name || 'System'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
