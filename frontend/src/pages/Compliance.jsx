import React, { useEffect, useState } from 'react'
import { complianceApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Compliance() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    complianceApi.alerts(user.dealerId).then((res) => setAlerts(res.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load compliance data'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>

  return (
    <div className="card p-5">
      <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Compliance alerts</div>
      {alerts.length === 0 ? (
        <div className="text-ink-muted text-sm">No expired or expiring compliance documents.</div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-line last:border-0 text-sm">
              <div>
                <div className="text-ink-primary">{a.entity_label} ({a.entity_type})</div>
                <div className="text-ink-muted text-xs">{a.doc_type} · expires {a.expiry_date}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="data-num text-ink-secondary text-xs">{a.days_to_expiry} days</span>
                <StatusBadge status={a.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
