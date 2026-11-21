import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('frontdesk_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('frontdesk_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const getMe = () =>
  api.get('/auth/me').then(r => r.data)

// Tickets
export const getTickets = (filters = {}) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      params.append(key, value)
    }
  })
  return api.get(`/tickets?${params.toString()}`).then(r => r.data)
}

export const getTicket = (id) =>
  api.get(`/tickets/${id}`).then(r => r.data)

export const createTicket = (data) =>
  api.post('/tickets', data).then(r => r.data)

export const claimTicket = (id) =>
  api.post(`/tickets/${id}/claim`).then(r => r.data)

export const updateTicket = (id, data) =>
  api.patch(`/tickets/${id}`, data).then(r => r.data)

export const addMessage = (ticketId, content, isInternal = false) =>
  api.post(`/tickets/${ticketId}/messages`, { content, is_internal: isInternal }).then(r => r.data)

export const reopenTicket = (id) =>
  api.post(`/tickets/${id}/reopen`).then(r => r.data)

// Admin
export const getStats = () =>
  api.get('/admin/stats').then(r => r.data)

export const getAgents = () =>
  api.get('/admin/agents').then(r => r.data)

export const createAgent = (data) =>
  api.post('/admin/agents', data).then(r => r.data)

export const updateAgent = (id, data) =>
  api.patch(`/admin/agents/${id}`, data).then(r => r.data)

export const getHolidays = () =>
  api.get('/admin/holidays').then(r => r.data)

export const createHoliday = (data) =>
  api.post('/admin/holidays', data).then(r => r.data)

export const deleteHoliday = (id) =>
  api.delete(`/admin/holidays/${id}`).then(r => r.data)

export const getAuditLogs = (filters = {}) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      params.append(key, value)
    }
  })
  return api.get(`/admin/audit?${params.toString()}`).then(r => r.data)
}

export default api
