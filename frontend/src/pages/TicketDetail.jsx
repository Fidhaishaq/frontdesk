import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getTicket, claimTicket, updateTicket, addMessage, reopenTicket, getAgents, getErrorMessage } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/Toast'

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = new Date(dateStr) - new Date()
  const absDiff = Math.abs(diff)
  const hours = Math.floor(absDiff / 3600000)
  const minutes = Math.floor((absDiff % 3600000) / 60000)
  if (diff > 0) return `${hours}h ${minutes}m remaining`
  return `${hours}h ${minutes}m overdue`
}

export default function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isAdmin } = useAuth()
  const toast = useToast()

  const [ticket, setTicket] = useState(null)
  const [messages, setMessages] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [replyContent, setReplyContent] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [sending, setSending] = useState(false)
  const [showAudit, setShowAudit] = useState(false)

  useEffect(() => {
    loadTicket()
    loadAgents()
  }, [id])

  const loadTicket = async () => {
    try {
      const data = await getTicket(id)
      setTicket(data.ticket)
      setMessages(data.messages || [])
      setAuditLogs(data.audit_logs || [])
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load ticket'))
      navigate('/tickets')
    } finally {
      setLoading(false)
    }
  }

  const loadAgents = async () => {
    try {
      const data = await getAgents()
      setAgents(data.agents || [])
    } catch (err) { /* ok for non-admin */ }
  }

  const handleClaim = async () => {
    try {
      await claimTicket(id)
      toast.success('Ticket claimed!')
      loadTicket()
    } catch (err) {
      const msg = getErrorMessage(err, 'Failed to claim ticket')
      toast.error(msg)
    }
  }

  const handleStatusChange = async (newStatus) => {
    try {
      await updateTicket(id, { status: newStatus })
      toast.success(`Status changed to ${newStatus.replace(/_/g, ' ')}`)
      loadTicket()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update status'))
    }
  }

  const handlePriorityChange = async (newPriority) => {
    try {
      await updateTicket(id, { priority: newPriority })
      toast.success(`Priority changed to ${newPriority}`)
      loadTicket()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update priority'))
    }
  }

  const handleAgentAssign = async (agentId) => {
    try {
      await updateTicket(id, { assigned_agent_id: agentId || null })
      toast.success('Agent updated')
      loadTicket()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to assign agent'))
    }
  }

  const handleReopen = async () => {
    try {
      await reopenTicket(id)
      toast.success('Ticket reopened')
      loadTicket()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Cannot reopen ticket'))
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!replyContent.trim()) return
    setSending(true)
    try {
      await addMessage(id, replyContent, isInternal)
      toast.success(isInternal ? 'Internal note added' : 'Reply sent')
      setReplyContent('')
      loadTicket()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to send message'))
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <div className="spinner-container"><div className="spinner"></div></div>
  }

  if (!ticket) return null

  const canReopen = (ticket.status === 'resolved' || ticket.status === 'closed')
  const statusOptions = ['open', 'in_progress', 'waiting_for_customer', 'resolved', 'closed']

  const getAuditDotClass = (action) => {
    if (action.includes('created')) return 'created'
    if (action.includes('status')) return 'status'
    if (action.includes('priority')) return 'priority'
    if (action.includes('assign') || action.includes('claim')) return 'assigned'
    if (action.includes('note') || action.includes('reply') || action.includes('message')) return 'message'
    if (action.includes('close') || action.includes('resolved')) return 'closed'
    return ''
  }

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/tickets">Tickets</Link>
        <span className="breadcrumb-separator">›</span>
        <span>{ticket.ticket_number}</span>
      </div>

      <div className="ticket-detail-layout">
        {/* Left Column - Main Content */}
        <div className="ticket-main">
          {/* Ticket Header */}
          <div className="card">
            <div className="ticket-header">
              <div className="ticket-header-info">
                <div className="ticket-number">{ticket.ticket_number}</div>
                <h1 className="ticket-subject">{ticket.subject}</h1>
                <div className="ticket-badges">
                  <span className={`badge badge-${ticket.priority}`}>{ticket.priority}</span>
                  <span className={`badge badge-${ticket.status}`}>{ticket.status.replace(/_/g, ' ')}</span>
                  {ticket.sla_status === 'overdue' && <span className="badge badge-overdue">Overdue</span>}
                  {ticket.status === 'waiting_for_customer' && <span className="badge badge-paused">SLA Paused</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Customer Info */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Customer Information</h3>
            </div>
            <div className="ticket-info-grid">
              <div className="ticket-info-item">
                <span className="ticket-info-label">Name</span>
                <span className="ticket-info-value">{ticket.customer_name}</span>
              </div>
              <div className="ticket-info-item">
                <span className="ticket-info-label">Email</span>
                <span className="ticket-info-value">{ticket.customer_email}</span>
              </div>
            </div>
            <div style={{ marginTop: '12px' }}>
              <span className="ticket-info-label">Description</span>
              <p style={{ marginTop: '4px', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{ticket.description}</p>
            </div>
          </div>

          {/* Messages Thread */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Conversation</h3>
              <span className="text-muted" style={{ fontSize: '0.8125rem' }}>{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
            </div>

            {messages.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 0' }}>
                <p className="text-muted">No messages yet. Start the conversation below.</p>
              </div>
            ) : (
              <div className="message-thread">
                {messages.map(msg => (
                  <div key={msg.id} className={`message-bubble ${msg.is_internal ? 'internal-note' : msg.user_id ? 'agent-message' : 'customer-message'}`}>
                    <div className="message-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="message-sender">{msg.sender_name}</span>
                        {msg.is_internal && <span className="message-label internal">🔒 Internal Note</span>}
                        {!msg.is_internal && msg.user_id && <span className="message-label agent">Agent</span>}
                        {!msg.is_internal && !msg.user_id && <span className="message-label customer">Customer</span>}
                      </div>
                      <span className="message-time">{formatDate(msg.created_at)}</span>
                    </div>
                    <div className="message-content">{msg.content}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Reply Composer */}
            {ticket.status !== 'closed' && (
              <div className="reply-composer">
                <div className="reply-tabs">
                  <button className={`reply-tab ${!isInternal ? 'active' : ''}`} onClick={() => setIsInternal(false)}>
                    💬 Reply to Customer
                  </button>
                  <button className={`reply-tab internal ${isInternal ? 'active' : ''}`} onClick={() => setIsInternal(true)}>
                    🔒 Internal Note
                  </button>
                </div>
                <form onSubmit={handleSendMessage}>
                  <textarea
                    className="form-textarea"
                    placeholder={isInternal ? 'Add an internal note (not visible to customer)...' : 'Type your reply to the customer...'}
                    value={replyContent}
                    onChange={e => setReplyContent(e.target.value)}
                    rows={3}
                    style={isInternal ? { borderColor: '#fde68a', background: '#fffef5' } : {}}
                  />
                  <div className="reply-actions">
                    <button type="submit" className={`btn ${isInternal ? 'btn-warning' : 'btn-primary'}`} disabled={sending || !replyContent.trim()}>
                      {sending ? 'Sending...' : isInternal ? '🔒 Add Note' : '💬 Send Reply'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Sidebar */}
        <div className="ticket-sidebar">
          {/* Actions */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Actions</h3>
            </div>

            {/* Claim Button */}
            {!ticket.assigned_agent_id && ticket.status === 'open' && (
              <button className="btn btn-primary btn-block" onClick={handleClaim} style={{ marginBottom: '12px' }}>
                🙋 Claim Ticket
              </button>
            )}

            {/* Status */}
            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={ticket.status}
                onChange={e => handleStatusChange(e.target.value)}
                disabled={ticket.status === 'closed'}
              >
                {statusOptions.map(s => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>

            {/* Priority */}
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                value={ticket.priority}
                onChange={e => handlePriorityChange(e.target.value)}
              >
                <option value="urgent">Urgent</option>
                <option value="medium">Medium</option>
                <option value="small">Small</option>
              </select>
            </div>

            {/* Assigned Agent */}
            {isAdmin && (
              <div className="form-group">
                <label className="form-label">Assigned Agent</label>
                <select
                  className="form-select"
                  value={ticket.assigned_agent_id || ''}
                  onChange={e => handleAgentAssign(e.target.value ? parseInt(e.target.value) : null)}
                >
                  <option value="">Unassigned</option>
                  {agents.filter(a => a.is_active).map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Reopen */}
            {canReopen && (
              <button className="btn btn-secondary btn-block" onClick={handleReopen} style={{ marginTop: '8px' }}>
                🔄 Reopen Ticket
              </button>
            )}
          </div>

          {/* SLA Info */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">SLA Information</h3>
            </div>
            <div className="sla-info">
              <div className={`sla-item ${ticket.is_response_overdue ? 'overdue' : ''}`}>
                <div>
                  <div className="sla-item-label">First Response</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                    {ticket.first_response_at ? `Responded ${formatDate(ticket.first_response_at)}` : formatDate(ticket.response_deadline)}
                  </div>
                </div>
                <div className={`sla-item-value ${ticket.first_response_at ? 'on-time' : ticket.is_response_overdue ? 'overdue' : ticket.status === 'waiting_for_customer' ? 'paused' : 'on-time'}`}>
                  {ticket.first_response_at ? '✓' : ticket.is_response_overdue ? '⚠ Overdue' : ticket.status === 'waiting_for_customer' ? '⏸ Paused' : '● On Time'}
                </div>
              </div>
              <div className={`sla-item ${ticket.is_resolution_overdue ? 'overdue' : ''}`}>
                <div>
                  <div className="sla-item-label">Resolution</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                    {ticket.resolved_at ? `Resolved ${formatDate(ticket.resolved_at)}` : formatDate(ticket.resolution_deadline)}
                  </div>
                </div>
                <div className={`sla-item-value ${ticket.resolved_at ? 'on-time' : ticket.is_resolution_overdue ? 'overdue' : ticket.status === 'waiting_for_customer' ? 'paused' : 'on-time'}`}>
                  {ticket.resolved_at ? '✓' : ticket.is_resolution_overdue ? '⚠ Overdue' : ticket.status === 'waiting_for_customer' ? '⏸ Paused' : '● On Time'}
                </div>
              </div>
            </div>
          </div>

          {/* Ticket Details */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Details</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="ticket-info-item">
                <span className="ticket-info-label">Agent</span>
                <span className="ticket-info-value">{ticket.assigned_agent_name || 'Unassigned'}</span>
              </div>
              <div className="ticket-info-item">
                <span className="ticket-info-label">Created</span>
                <span className="ticket-info-value">{formatDate(ticket.created_at)}</span>
              </div>
              <div className="ticket-info-item">
                <span className="ticket-info-label">Updated</span>
                <span className="ticket-info-value">{formatDate(ticket.updated_at)}</span>
              </div>
            </div>
          </div>

          {/* Audit Trail */}
          <div className="card">
            <div className="card-header" style={{ cursor: 'pointer' }} onClick={() => setShowAudit(!showAudit)}>
              <h3 className="card-title">Audit Trail</h3>
              <span style={{ color: '#94a3b8' }}>{showAudit ? '▲' : '▼'} {auditLogs.length}</span>
            </div>
            {showAudit && (
              <div className="audit-timeline">
                {auditLogs.map((log, idx) => (
                  <div key={log.id || idx} className="audit-item">
                    <div className={`audit-dot ${getAuditDotClass(log.action)}`}></div>
                    <div className="audit-content">
                      <div className="audit-action">{log.action.replace(/_/g, ' ')}</div>
                      {(log.old_value || log.new_value) && (
                        <div className="audit-values">
                          {log.old_value && <span>{log.old_value}</span>}
                          {log.old_value && log.new_value && <span> → </span>}
                          {log.new_value && <span>{log.new_value}</span>}
                        </div>
                      )}
                      <div className="audit-meta">{log.user_name || 'System'} · {formatDate(log.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
