import React, { useEffect, useState } from 'react'
import { maintenanceApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Maintenance() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    maintenanceApi.alerts(user.dealerId).then((res) => setAlerts(res.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load maintenance data'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>

  return (
    <div className="card p-5">
      <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Maintenance risk</div>
      <div className="space-y-2">
        {alerts.map((a) => (
          <div key={a.tanker_id} className="py-2 border-b border-line last:border-0 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-ink-primary font-medium">{a.tanker_code}</span>
              <div className="flex items-center gap-3">
                <span className="data-num text-ink-secondary text-xs">{a.risk_score}/100</span>
                <StatusBadge status={a.risk_level} />
              </div>
            </div>
            <p className="text-ink-secondary text-xs mt-1">{a.reason}</p>
            <p className="text-ink-muted text-xs mt-0.5">Recommended service by {a.recommended_service_date}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
