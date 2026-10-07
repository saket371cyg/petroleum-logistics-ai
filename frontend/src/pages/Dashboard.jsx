import React, { useEffect, useState } from 'react'
import { analyticsApi, inventoryApi, dispatchApi, complianceApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { user } = useAuth()
  const [analytics, setAnalytics] = useState(null)
  const [risks, setRisks] = useState([])
  const [dispatches, setDispatches] = useState([])
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    Promise.all([
      analyticsApi.get(user.dealerId),
      inventoryApi.getRisk(user.dealerId),
      dispatchApi.list(user.dealerId),
      complianceApi.alerts(user.dealerId),
    ])
      .then(([a, r, d, c]) => {
        setAnalytics(a.data)
        setRisks(r.data)
        setDispatches(d.data.slice(0, 5))
        setAlerts(c.data.filter((x) => x.status !== 'VALID').slice(0, 5))
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load dashboard data'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>
  if (!analytics) return <div className="text-ink-secondary text-sm">Loading…</div>

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Petrol stock" value={`${analytics.petrol_stock_l.toLocaleString()} L`} />
        <MetricCard label="Diesel stock" value={`${analytics.diesel_stock_l.toLocaleString()} L`} />
        <MetricCard label="Pending orders" value={analytics.pending_orders} />
        <MetricCard label="Active dispatches" value={analytics.active_dispatches} />
        <MetricCard label="Available tankers" value={analytics.available_tankers} />
        <MetricCard label="Fleet utilization" value={`${analytics.fleet_utilization_pct}%`} />
        <MetricCard
          label="Critical alerts"
          value={analytics.critical_alerts}
          accent={analytics.critical_alerts > 0}
        />
        <MetricCard
          label="Avg delivery time"
          value={analytics.avg_delivery_hours != null ? `${analytics.avg_delivery_hours} h` : '—'}
        />
      </div>

      <div className="card p-4">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-2">Executive summary</div>
        <p className="text-ink-primary text-sm leading-relaxed">{analytics.summary_text}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-ink-secondary text-xs uppercase tracking-wide">Inventory risk</div>
            <Link to="/inventory" className="text-amber text-xs hover:underline">View all</Link>
          </div>
          <div className="space-y-2">
            {risks.map((r) => (
              <div key={r.fuel_type} className="flex items-center justify-between text-sm py-1.5 border-b border-line last:border-0">
                <span className="text-ink-primary">{r.fuel_type}</span>
                <span className="data-num text-ink-secondary">{r.days_of_stock} days</span>
                <StatusBadge status={r.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-ink-secondary text-xs uppercase tracking-wide">Recent dispatches</div>
            <Link to="/dispatch" className="text-amber text-xs hover:underline">View all</Link>
          </div>
          <div className="space-y-2">
            {dispatches.length === 0 && <div className="text-ink-muted text-sm">No dispatches yet.</div>}
            {dispatches.map((d) => (
              <div key={d.id} className="flex items-center justify-between text-sm py-1.5 border-b border-line last:border-0">
                <span className="text-ink-primary">Dispatch #{d.id}</span>
                <span className="text-ink-secondary text-xs">{d.status}</span>
                <StatusBadge status={d.risk_level || 'NORMAL'} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-ink-secondary text-xs uppercase tracking-wide">Compliance alerts</div>
          <Link to="/compliance" className="text-amber text-xs hover:underline">View all</Link>
        </div>
        {alerts.length === 0 ? (
          <div className="text-ink-muted text-sm">No active compliance alerts.</div>
        ) : (
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-line last:border-0">
                <span className="text-ink-primary">{a.entity_label} — {a.doc_type}</span>
                <span className="text-ink-secondary text-xs">{a.days_to_expiry} days to expiry</span>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
