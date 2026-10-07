import React from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Inventory from './pages/Inventory'
import Orders from './pages/Orders'
import Forecast from './pages/Forecast'
import Fleet from './pages/Fleet'
import Dispatch from './pages/Dispatch'
import RefinerySlots from './pages/RefinerySlots'
import Compliance from './pages/Compliance'
import Maintenance from './pages/Maintenance'
import Analytics from './pages/Analytics'
import AIAssistant from './pages/AIAssistant'

const TITLES = {
  '/dashboard': 'Dashboard',
  '/inventory': 'Inventory',
  '/orders': 'Orders',
  '/forecast': 'Demand forecast',
  '/fleet': 'Fleet',
  '/dispatch': 'Dispatch',
  '/refinery-slots': 'Refinery loading slots',
  '/compliance': 'Compliance',
  '/maintenance': 'Maintenance',
  '/analytics': 'Analytics',
  '/ai-assistant': 'AI assistant',
}

function ProtectedLayout({ children }) {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex bg-canvas min-h-screen">
      <Sidebar />
      <div className="flex-1 min-w-0">
        <Topbar title={TITLES[location.pathname] || 'Petro Ops'} />
        <main className="p-6 max-w-6xl">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<ProtectedLayout><Dashboard /></ProtectedLayout>} />
      <Route path="/inventory" element={<ProtectedLayout><Inventory /></ProtectedLayout>} />
      <Route path="/orders" element={<ProtectedLayout><Orders /></ProtectedLayout>} />
      <Route path="/forecast" element={<ProtectedLayout><Forecast /></ProtectedLayout>} />
      <Route path="/fleet" element={<ProtectedLayout><Fleet /></ProtectedLayout>} />
      <Route path="/dispatch" element={<ProtectedLayout><Dispatch /></ProtectedLayout>} />
      <Route path="/refinery-slots" element={<ProtectedLayout><RefinerySlots /></ProtectedLayout>} />
      <Route path="/compliance" element={<ProtectedLayout><Compliance /></ProtectedLayout>} />
      <Route path="/maintenance" element={<ProtectedLayout><Maintenance /></ProtectedLayout>} />
      <Route path="/analytics" element={<ProtectedLayout><Analytics /></ProtectedLayout>} />
      <Route path="/ai-assistant" element={<ProtectedLayout><AIAssistant /></ProtectedLayout>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
