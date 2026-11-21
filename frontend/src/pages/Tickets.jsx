import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getTickets, createTicket, getAgents } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/Toast'
import Modal from '../components/Modal'

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

export default function Tickets() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAdmin } = useAuth()
  const toast = useToast()

  const [tickets, setTickets] = useState([])
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)

  // Filters
  const [filters, setFilters] = useState({
    status: searchParams.get('status') || 'all',
    priority: searchParams.get('priority') || 'all',
    agent_id: searchParams.get('agent_id') || 'all',
    search: searchParams.get('search') || '',
    overdue: searchParams.get('overdue') || ''
  })

  // Create form
  const [form, setForm] = useState({
    customer_name: '', customer_email: '', subject: '', description: '', priority: 'medium'
  })

  useEffect(() => {
    loadTickets()
    loadAgents()
  }, [])

  useEffect(() => {
    loadTickets()
  }, [filters])

  const loadTickets = async () => {
    try {
      const data = await getTickets(filters)
      setTickets(data.tickets || [])
    } catch (err) {
      console.error('Failed to load tickets:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadAgents = async () => {
    try {
      const data = await getAgents()
      setAgents(data.agents || [])
    } catch (err) {
      // Non-admin may not have access, that's ok
    }
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.customer_name.trim() || !form.customer_email.trim() || !form.subject.trim() || !form.description.trim()) {
      toast.error('All fields are required')
      return
    }
    setCreating(true)
    try {
      const data = await createTicket(form)
      toast.success(`Ticket ${data.ticket.ticket_number} created!`)
      setShowCreate(false)
      setForm({ customer_name: '', customer_email: '', subject: '', description: '', priority: 'medium' })
      loadTickets()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create ticket')
    } finally {
      setCreating(false)
    }
  }

  const getSlaClass = (ticket) => {
    if (ticket.status === 'closed' || ticket.status === 'resolved') return ''
    if (ticket.sla_status === 'overdue' || ticket.sla_status === 'breached') return 'badge-overdue'
    if (ticket.status === 'waiting_for_customer') return 'badge-paused'
    return 'badge-on-time'
  }

  const getSlaLabel = (ticket) => {
    if (ticket.status === 'closed' || ticket.status === 'resolved') return 'Done'
    if (ticket.sla_status === 'overdue' || ticket.sla_status === 'breached') return 'Overdue'
    if (ticket.status === 'waiting_for_customer') return 'Paused'
    return 'On Time'
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Tickets</h1>
          <p className="page-subtitle">{tickets.length} ticket{tickets.length !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Create Ticket
        </button>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <input
          className="form-input"
          type="text"
          placeholder="🔍 Search tickets..."
          value={filters.search}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          style={{ minWidth: '200px' }}
        />
        <select className="form-select" value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="waiting_for_customer">Waiting for Customer</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select className="form-select" value={filters.priority} onChange={(e) => handleFilterChange('priority', e.target.value)}>
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="medium">Medium</option>
          <option value="small">Small</option>
        </select>
        {agents.length > 0 && (
          <select className="form-select" value={filters.agent_id} onChange={(e) => handleFilterChange('agent_id', e.target.value)}>
            <option value="all">All Agents</option>
            <option value="unassigned">Unassigned</option>
            {agents.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        )}
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
          <input
            type="checkbox"
            checked={filters.overdue === 'true'}
            onChange={(e) => handleFilterChange('overdue', e.target.checked ? 'true' : '')}
          />
          🔥 Overdue Only
        </label>
      </div>

      {/* Table */}
      {loading ? (
        <div className="spinner-container"><div className="spinner"></div></div>
      ) : tickets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎫</div>
          <div className="empty-state-title">No tickets found</div>
          <p className="empty-state-text">Try adjusting your filters or create a new ticket.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="table table-clickable">
            <thead>
              <tr>
                <th>Ticket ID</th>
                <th>Subject</th>
                <th>Customer</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Agent</th>
                <th>SLA</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map(ticket => (
                <tr key={ticket.id} onClick={() => navigate(`/tickets/${ticket.id}`)}>
                  <td className="ticket-id">{ticket.ticket_number}</td>
                  <td style={{ maxWidth: '250px' }} className="truncate">{ticket.subject}</td>
                  <td>{ticket.customer_name}</td>
                  <td><span className={`badge badge-${ticket.priority}`}>{ticket.priority}</span></td>
                  <td><span className={`badge badge-${ticket.status}`}>{ticket.status.replace(/_/g, ' ')}</span></td>
                  <td className="text-muted">{ticket.assigned_agent_name || '—'}</td>
                  <td><span className={`badge ${getSlaClass(ticket)}`}>{getSlaLabel(ticket)}</span></td>
                  <td className="text-muted" style={{ whiteSpace: 'nowrap' }}>{formatDate(ticket.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Ticket Modal */}
      {showCreate && (
        <Modal title="Create New Ticket" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Customer Name *</label>
                <input className="form-input" value={form.customer_name} onChange={e => setForm(f => ({ ...f, customer_name: e.target.value }))} placeholder="John Doe" required />
              </div>
              <div className="form-group">
                <label className="form-label">Customer Email *</label>
                <input className="form-input" type="email" value={form.customer_email} onChange={e => setForm(f => ({ ...f, customer_email: e.target.value }))} placeholder="john@example.com" required />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Subject *</label>
              <input className="form-input" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Brief description of the issue" required />
            </div>
            <div className="form-group">
              <label className="form-label">Description *</label>
              <textarea className="form-textarea" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Detailed description of the issue..." rows={4} required />
            </div>
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select className="form-select" value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                <option value="urgent">Urgent</option>
                <option value="medium">Medium</option>
                <option value="small">Small</option>
              </select>
            </div>
            <div className="modal-footer" style={{ padding: '16px 0 0', border: 'none' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={creating}>
                {creating ? 'Creating...' : 'Create Ticket'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
