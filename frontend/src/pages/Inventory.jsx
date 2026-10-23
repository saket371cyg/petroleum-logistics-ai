import React, { useEffect, useState } from 'react'
import { inventoryApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Inventory() {
  const { user } = useAuth()
  const [inventory, setInventory] = useState([])
  const [risks, setRisks] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Edit / Calibrate Modal state
  const [editingInv, setEditingInv] = useState(null)
  const [editLevel, setEditLevel] = useState('')
  const [editReorder, setEditReorder] = useState('')
  const [editSafety, setEditSafety] = useState('')
  const [saveError, setSaveError] = useState('')

  const loadData = () => {
    if (!user) return
    Promise.all([inventoryApi.get(user.dealerId), inventoryApi.getRisk(user.dealerId)])
      .then(([inv, risk]) => {
        setInventory(inv.data)
        setRisks(risk.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load inventory'))
  }

  useEffect(() => {
    loadData()
  }, [user])

  const riskFor = (fuelType) => risks.find((r) => r.fuel_type === fuelType)

  const handleSimulateSales = async () => {
    setMessage('')
    setError('')
    setBusy(true)
    try {
      await inventoryApi.simulateConsumption(user.dealerId, { days: 1.0 })
      setMessage('Simulated 1 day of retail fuel sales! Tank levels depleted based on daily demand.')
      loadData()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to simulate sales consumption')
    } finally {
      setBusy(false)
    }
  }

  const openEditModal = (inv) => {
    setEditingInv(inv)
    setEditLevel(inv.current_level_l.toString())
    setEditReorder(inv.reorder_point_l.toString())
    setEditSafety(inv.safety_stock_l.toString())
    setSaveError('')
  }

  const handleSaveCalibration = async (e) => {
    e.preventDefault()
    setSaveError('')
    const level = parseFloat(editLevel)
    const reorder = parseFloat(editReorder)
    const safety = parseFloat(editSafety)

    if (isNaN(level) || level < 0) {
      setSaveError('Please enter a valid stock level (≥ 0 L)')
      return
    }
    if (level > editingInv.tank_capacity_l) {
      setSaveError(`Level cannot exceed capacity (${editingInv.tank_capacity_l.toLocaleString()} L)`)
      return
    }

    setBusy(true)
    try {
      await inventoryApi.update(user.dealerId, editingInv.fuel_type, {
        current_level_l: level,
        reorder_point_l: isNaN(reorder) ? undefined : reorder,
        safety_stock_l: isNaN(safety) ? undefined : safety,
      })
      setMessage(`Updated ${editingInv.fuel_type} inventory & thresholds successfully.`)
      setEditingInv(null)
      loadData()
    } catch (err) {
      setSaveError(err.response?.data?.detail || 'Failed to save inventory updates')
    } finally {
      setBusy(false)
    }
  }

  const applyPreset = (type) => {
    if (!editingInv) return
    if (type === 'critical') {
      setEditLevel((editingInv.reorder_point_l * 0.4).toFixed(0))
    } else if (type === '80pct') {
      setEditLevel((editingInv.tank_capacity_l * 0.8).toFixed(0))
    } else if (type === '100pct') {
      setEditLevel(editingInv.tank_capacity_l.toFixed(0))
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Action Bar */}
      <div className="card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div>
          <h2 className="text-ink-primary font-medium text-base">Underground Fuel Storage Tanks</h2>
          <p className="text-ink-secondary text-xs mt-0.5">
            Monitor real-time tank volumes, automated ATG dip readings, and reorder thresholds.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSimulateSales}
            disabled={busy}
            className="bg-surface-2 hover:bg-surface-3 text-ink-primary border border-line text-xs font-medium px-3.5 py-2 rounded transition-colors disabled:opacity-50 flex items-center gap-1.5"
            title="Deducts 1 day of predicted fuel sales to test stockout alerts"
          >
            <span>📉</span>
            <span>{busy ? 'Simulating…' : 'Simulate 1-Day Sales'}</span>
          </button>
        </div>
      </div>

      {message && (
        <div className="bg-good-soft border border-good text-good text-sm p-3 rounded flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="text-xs text-good hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {error && <div className="text-bad text-sm p-3 bg-bad-soft border border-bad rounded">{error}</div>}

      {/* Tanks List */}
      <div className="space-y-4">
        {inventory.map((inv) => {
          const risk = riskFor(inv.fuel_type)
          const pct = Math.min(100, (inv.current_level_l / inv.tank_capacity_l) * 100)
          return (
            <div key={inv.id} className="card p-5 transition-shadow hover:border-line-strong">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div>
                    <div className="text-ink-primary font-medium text-base flex items-center gap-2">
                      {inv.fuel_type}
                      <span className="text-xs text-ink-muted font-normal">Tank #{inv.id}</span>
                    </div>
                    <div className="text-ink-muted text-xs mt-0.5">
                      Last sensor sync / dip reading: {new Date(inv.updated_at).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {risk && <StatusBadge status={risk.status} />}
                  <button
                    onClick={() => openEditModal(inv)}
                    className="text-xs border border-line hover:border-line-strong text-ink-primary bg-surface-2 hover:bg-surface-3 px-3 py-1.5 rounded transition-colors flex items-center gap-1"
                  >
                    <span>✏️</span>
                    <span>Calibrate / Edit</span>
                  </button>
                </div>
              </div>

              {/* Tank Level Progress Bar */}
              <div className="w-full h-3.5 bg-surface-2 rounded-full overflow-hidden mb-3 border border-line">
                <div
                  className={`h-full transition-all duration-500 ${
                    pct < 25 ? 'bg-bad' : pct < 50 ? 'bg-warn' : 'bg-good'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm pt-1">
                <div>
                  <div className="text-ink-muted text-xs">Current Level</div>
                  <div className="data-num text-ink-primary text-base font-semibold">
                    {inv.current_level_l.toLocaleString()} L
                  </div>
                  <div className="text-ink-muted text-[11px]">{pct.toFixed(1)}% full</div>
                </div>
                <div>
                  <div className="text-ink-muted text-xs">Tank Capacity</div>
                  <div className="data-num text-ink-primary">{inv.tank_capacity_l.toLocaleString()} L</div>
                </div>
                <div>
                  <div className="text-ink-muted text-xs">Reorder Point</div>
                  <div className="data-num text-ink-primary">{inv.reorder_point_l.toLocaleString()} L</div>
                </div>
                <div>
                  <div className="text-ink-muted text-xs">Safety Stock</div>
                  <div className="data-num text-ink-primary">{inv.safety_stock_l.toLocaleString()} L</div>
                </div>
                <div>
                  <div className="text-ink-muted text-xs">Days of Stock</div>
                  <div className="data-num text-ink-primary font-medium">
                    {risk ? `${risk.days_of_stock.toFixed(1)} days` : '—'}
                  </div>
                  {risk && (
                    <div className="text-ink-muted text-[11px]">
                      ~{risk.predicted_daily_demand_l.toFixed(0)} L/day
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Edit / Calibration Modal */}
      {editingInv && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg p-6 bg-surface border-line-strong shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <div>
                <h3 className="text-ink-primary font-semibold text-base">
                  Calibrate & Edit {editingInv.fuel_type} Tank
                </h3>
                <p className="text-ink-muted text-xs">
                  Max capacity: {editingInv.tank_capacity_l.toLocaleString()} Liters
                </p>
              </div>
              <button
                onClick={() => setEditingInv(null)}
                className="text-ink-muted hover:text-ink-primary text-lg px-2"
              >
                ✕
              </button>
            </div>

            {saveError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {saveError}
              </div>
            )}

            <form onSubmit={handleSaveCalibration} className="space-y-4">
              <div>
                <label className="block text-ink-secondary text-xs mb-1.5">
                  Current Stock Level (Liters)
                </label>
                <input
                  type="number"
                  step="any"
                  value={editLevel}
                  onChange={(e) => setEditLevel(e.target.value)}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                  required
                />
              </div>

              {/* Quick Presets */}
              <div>
                <div className="text-ink-muted text-[11px] mb-1.5">Quick Presets for Testing:</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => applyPreset('critical')}
                    className="text-xs bg-bad-soft border border-bad text-bad px-2.5 py-1 rounded hover:opacity-90 transition-opacity"
                  >
                    🚨 Drop to Critical (~{(editingInv.reorder_point_l * 0.4).toFixed(0)} L)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('80pct')}
                    className="text-xs bg-surface-2 border border-line text-ink-secondary px-2.5 py-1 rounded hover:text-ink-primary"
                  >
                    80% Level ({(editingInv.tank_capacity_l * 0.8).toLocaleString()} L)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('100pct')}
                    className="text-xs bg-good-soft border border-good text-good px-2.5 py-1 rounded hover:opacity-90"
                  >
                    100% Full ({editingInv.tank_capacity_l.toLocaleString()} L)
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1.5">
                    Reorder Point (Liters)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={editReorder}
                    onChange={(e) => setEditReorder(e.target.value)}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1.5">
                    Safety Stock (Liters)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={editSafety}
                    onChange={(e) => setEditSafety(e.target.value)}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-line">
                <button
                  type="button"
                  onClick={() => setEditingInv(null)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary hover:border-line-strong transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-5 py-2 rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {busy ? 'Saving…' : 'Save Calibration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
