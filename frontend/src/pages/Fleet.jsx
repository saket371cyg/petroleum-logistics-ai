import React, { useEffect, useState } from 'react'
import { fleetApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Fleet() {
  const { user } = useAuth()
  const [tankers, setTankers] = useState([])
  const [drivers, setDrivers] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    Promise.all([fleetApi.tankers(user.dealerId), fleetApi.drivers(user.dealerId)])
      .then(([t, d]) => {
        setTankers(t.data)
        setDrivers(d.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load fleet data'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Tankers</div>
        <div className="grid md:grid-cols-2 gap-3">
          {tankers.map((t) => (
            <div key={t.id} className="bg-surface-2 rounded p-3 flex items-center justify-between">
              <div>
                <div className="text-ink-primary text-sm font-medium">{t.code}</div>
                <div className="text-ink-muted text-xs mt-0.5">
                  {t.capacity_l.toLocaleString()} L · {t.mileage_km.toLocaleString()} km · {t.age_years} yrs
                </div>
              </div>
              <StatusBadge status={t.status === 'AVAILABLE' ? 'NORMAL' : t.status === 'MAINTENANCE' ? 'CRITICAL' : 'WARNING'} />
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Drivers</div>
        <div className="grid md:grid-cols-2 gap-3">
          {drivers.map((d) => (
            <div key={d.id} className="bg-surface-2 rounded p-3 flex items-center justify-between">
              <div>
                <div className="text-ink-primary text-sm font-medium">{d.name}</div>
                <div className="text-ink-muted text-xs mt-0.5">
                  {d.license_number} · expires {d.license_expiry}
                </div>
              </div>
              <StatusBadge status={d.status === 'AVAILABLE' ? 'NORMAL' : 'WARNING'} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
