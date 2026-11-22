import { useState, useEffect } from 'react'
import { getHolidays, createHoliday, deleteHoliday, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import Modal from '../components/Modal'

export default function Holidays() {
  const toast = useToast()
  const [holidays, setHolidays] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ date: '', name: '' })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { loadHolidays() }, [])

  const loadHolidays = async () => {
    try {
      const data = await getHolidays()
      setHolidays(data.holidays || [])
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load holidays'))
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.date || !form.name.trim()) {
      toast.error('Date and name are required')
      return
    }
    setSubmitting(true)
    try {
      await createHoliday(form)
      toast.success('Holiday added')
      setShowAdd(false)
      setForm({ date: '', name: '' })
      loadHolidays()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to add holiday'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Remove this holiday?')) return
    try {
      await deleteHoliday(id)
      toast.success('Holiday removed')
      loadHolidays()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to remove holiday'))
    }
  }

  if (loading) {
    return <div className="spinner-container"><div className="spinner"></div></div>
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Holiday Calendar</h1>
          <p className="page-subtitle">Configure holidays excluded from SLA calculations</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Holiday</button>
      </div>

      {holidays.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <div className="empty-state-title">No holidays configured</div>
          <p className="empty-state-text">Add holidays to exclude them from SLA calculations.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Holiday Name</th>
                <th>Day</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {holidays.sort((a, b) => a.date.localeCompare(b.date)).map(h => {
                const d = new Date(h.date + 'T00:00:00')
                const dayName = d.toLocaleDateString('en-IN', { weekday: 'long' })
                return (
                  <tr key={h.id}>
                    <td style={{ fontWeight: 500 }}>
                      {d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td>{h.name}</td>
                    <td className="text-muted">{dayName}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(h.id)}>Remove</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <Modal title="Add Holiday" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleAdd}>
            <div className="form-group">
              <label className="form-label">Date *</label>
              <input className="form-input" type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} required />
            </div>
            <div className="form-group">
              <label className="form-label">Holiday Name *</label>
              <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Republic Day" required />
            </div>
            <div className="modal-footer" style={{ padding: '16px 0 0', border: 'none' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add Holiday'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
