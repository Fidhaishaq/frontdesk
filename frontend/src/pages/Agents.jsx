import { useState, useEffect } from 'react'
import { getAgents, createAgent, updateAgent } from '../services/api'
import { useToast } from '../components/Toast'
import Modal from '../components/Modal'

export default function Agents() {
  const toast = useToast()
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [editAgent, setEditAgent] = useState(null)
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { loadAgents() }, [])

  const loadAgents = async () => {
    try {
      const data = await getAgents()
      setAgents(data.agents || [])
    } catch (err) {
      toast.error('Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.email.trim() || !form.password) {
      toast.error('All fields are required')
      return
    }
    setSubmitting(true)
    try {
      await createAgent(form)
      toast.success('Agent created successfully')
      setShowAdd(false)
      setForm({ name: '', email: '', password: '' })
      loadAgents()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create agent')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await updateAgent(editAgent.id, {
        name: editAgent.name,
        email: editAgent.email,
        is_active: editAgent.is_active
      })
      toast.success('Agent updated')
      setEditAgent(null)
      loadAgents()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update agent')
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggleActive = async (agent) => {
    try {
      await updateAgent(agent.id, { is_active: !agent.is_active })
      toast.success(agent.is_active ? 'Agent deactivated' : 'Agent activated')
      loadAgents()
    } catch (err) {
      toast.error('Failed to update agent status')
    }
  }

  if (loading) {
    return <div className="spinner-container"><div className="spinner"></div></div>
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Agents</h1>
          <p className="page-subtitle">{agents.length} support agent{agents.length !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Agent</button>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Status</th>
              <th>Assigned Tickets</th>
              <th>Resolved Tickets</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {agents.map(agent => (
              <tr key={agent.id}>
                <td style={{ fontWeight: 500 }}>{agent.name}</td>
                <td className="text-muted">{agent.email}</td>
                <td>
                  <span className={`badge ${agent.is_active ? 'badge-active' : 'badge-inactive'}`}>
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{agent.assigned_ticket_count || 0}</td>
                <td>{agent.resolved_ticket_count || 0}</td>
                <td>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditAgent({ ...agent })}>Edit</button>
                    <button
                      className={`btn btn-sm ${agent.is_active ? 'btn-danger' : 'btn-success'}`}
                      onClick={() => handleToggleActive(agent)}
                    >
                      {agent.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Agent Modal */}
      {showAdd && (
        <Modal title="Add New Agent" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleAdd}>
            <div className="form-group">
              <label className="form-label">Full Name *</label>
              <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Agent name" required />
            </div>
            <div className="form-group">
              <label className="form-label">Email *</label>
              <input className="form-input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="agent@arvo.com" required />
            </div>
            <div className="form-group">
              <label className="form-label">Password *</label>
              <input className="form-input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Minimum 6 characters" required />
            </div>
            <div className="modal-footer" style={{ padding: '16px 0 0', border: 'none' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Creating...' : 'Create Agent'}</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Edit Agent Modal */}
      {editAgent && (
        <Modal title="Edit Agent" onClose={() => setEditAgent(null)}>
          <form onSubmit={handleEdit}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="form-input" value={editAgent.name} onChange={e => setEditAgent(a => ({ ...a, name: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="form-input" type="email" value={editAgent.email} onChange={e => setEditAgent(a => ({ ...a, email: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" checked={editAgent.is_active} onChange={e => setEditAgent(a => ({ ...a, is_active: e.target.checked }))} />
                Active
              </label>
            </div>
            <div className="modal-footer" style={{ padding: '16px 0 0', border: 'none' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setEditAgent(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Saving...' : 'Save Changes'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
