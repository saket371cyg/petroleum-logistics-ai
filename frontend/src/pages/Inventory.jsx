import React, { useEffect, useState } from 'react'
import { inventoryApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Inventory() {
  const { user } = useAuth()
  const [inventory, setInventory] = useState([])
  const [risks, setRisks] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    Promise.all([inventoryApi.get(user.dealerId), inventoryApi.getRisk(user.dealerId)])
      .then(([inv, risk]) => {
        setInventory(inv.data)
        setRisks(risk.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load inventory'))
  }, [user])

  if (error) return <div className="text-bad text-sm">{error}</div>

  const riskFor = (fuelType) => risks.find((r) => r.fuel_type === fuelType)

  return (
    <div className="space-y-4">
      {inventory.map((inv) => {
        const risk = riskFor(inv.fuel_type)
        const pct = Math.min(100, (inv.current_level_l / inv.tank_capacity_l) * 100)
        return (
          <div key={inv.id} className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-ink-primary font-medium">{inv.fuel_type}</div>
                <div className="text-ink-muted text-xs mt-0.5">
                  Updated {new Date(inv.updated_at).toLocaleString()}
                </div>
              </div>
              {risk && <StatusBadge status={risk.status} />}
            </div>

            <div className="w-full h-3 bg-surface-2 rounded-full overflow-hidden mb-3">
              <div
                className={`h-full ${pct < 25 ? 'bg-bad' : pct < 50 ? 'bg-warn' : 'bg-good'}`}
                style={{ width: `${pct}%` }}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-ink-muted text-xs">Current level</div>
                <div className="data-num text-ink-primary">{inv.current_level_l.toLocaleString()} L</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Tank capacity</div>
                <div className="data-num text-ink-primary">{inv.tank_capacity_l.toLocaleString()} L</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Reorder point</div>
                <div className="data-num text-ink-primary">{inv.reorder_point_l.toLocaleString()} L</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Days of stock</div>
                <div className="data-num text-ink-primary">{risk ? risk.days_of_stock : '—'}</div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
