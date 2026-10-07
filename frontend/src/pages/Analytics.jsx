import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { analyticsApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import MetricCard from '../components/MetricCard'

export default function Analytics() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    analyticsApi.get(user.dealerId).then((res) => setData(res.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load analytics'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>
  if (!data) return <div className="text-ink-secondary text-sm">Loading…</div>

  const chartData = [
    { name: 'Petrol stock (L)', value: data.petrol_stock_l },
    { name: 'Diesel stock (L)', value: data.diesel_stock_l },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Fleet utilization" value={`${data.fleet_utilization_pct}%`} />
        <MetricCard label="Active dispatches" value={data.active_dispatches} />
        <MetricCard label="Avg delivery" value={data.avg_delivery_hours != null ? `${data.avg_delivery_hours} h` : '—'} />
        <MetricCard label="Critical alerts" value={data.critical_alerts} accent={data.critical_alerts > 0} />
      </div>

      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-4">Current stock levels</div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2A333A" />
            <XAxis dataKey="name" stroke="#9AA7AE" fontSize={12} />
            <YAxis stroke="#9AA7AE" fontSize={12} />
            <Tooltip contentStyle={{ backgroundColor: '#1D242A', border: '1px solid #2A333A', borderRadius: 8 }} />
            <Bar dataKey="value" fill="#E8A23A" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card p-4">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-2">Summary</div>
        <p className="text-ink-primary text-sm leading-relaxed">{data.summary_text}</p>
        <p className="text-ink-muted text-xs mt-2">Generated {new Date(data.generated_at).toLocaleString()}</p>
      </div>
    </div>
  )
}
