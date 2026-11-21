import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Sidebar from './components/Sidebar'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import TicketDetail from './pages/TicketDetail'
import Agents from './pages/Agents'
import AuditHistory from './pages/AuditHistory'
import Holidays from './pages/Holidays'

export default function App() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="spinner-container" style={{ minHeight: '100vh' }}>
        <div className="spinner"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        <div className="app-content">
          <Routes>
            <Route path="/" element={
              <ProtectedRoute><Dashboard /></ProtectedRoute>
            } />
            <Route path="/tickets" element={
              <ProtectedRoute><Tickets /></ProtectedRoute>
            } />
            <Route path="/tickets/:id" element={
              <ProtectedRoute><TicketDetail /></ProtectedRoute>
            } />
            <Route path="/agents" element={
              <ProtectedRoute adminOnly><Agents /></ProtectedRoute>
            } />
            <Route path="/audit" element={
              <ProtectedRoute adminOnly><AuditHistory /></ProtectedRoute>
            } />
            <Route path="/holidays" element={
              <ProtectedRoute adminOnly><Holidays /></ProtectedRoute>
            } />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
