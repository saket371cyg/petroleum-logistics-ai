import React, { useEffect, useState } from 'react'
import { dispatchApi, ordersApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Dispatch() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [dispatches, setDispatches] = useState([])
  const [selectedOrderId, setSelectedOrderId] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => {
    if (!user) return
    ordersApi.list(user.dealerId).then((res) => setOrders(res.data.filter((o) => o.status === 'APPROVED')))
    dispatchApi.list(user.dealerId).then((res) => setDispatches(res.data))
  }

  useEffect(load, [user])

  const runOptimize = async () => {
    if (!selectedOrderId) return
    setError('')
    setResult(null)
    setBusy(true)
    try {
      const res = await dispatchApi.optimize(Number(selectedOrderId), 6)
      setResult(res.data)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Optimization failed')
    } finally {
      setBusy(false)
    }
  }

  const approve = async (id) => {
    setBusy(true)
    try {
      await dispatchApi.approve(id)
      load()
    } finally {
      setBusy(false)
    }
  }

  const complete = async (id) => {
    setBusy(true)
    try {
      await dispatchApi.complete(id)
      load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">
          Run dispatch optimization (hill climbing)
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={selectedOrderId}
            onChange={(e) => setSelectedOrderId(e.target.value)}
            className="bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary flex-1"
          >
            <option value="">Select an approved order…</option>
            {orders.map((o) => (
              <option key={o.id} value={o.id}>
                Order #{o.id} — {o.fuel_type} {o.quantity_l.toLocaleString()} L
              </option>
            ))}
          </select>
          <button
            onClick={runOptimize}
            disabled={!selectedOrderId || busy}
            className="bg-amber text-canvas text-sm font-medium rounded px-4 py-2 hover:opacity-90 disabled:opacity-50"
          >
            Optimize
          </button>
        </div>
        {orders.length === 0 && (
          <p className="text-ink-muted text-xs mt-2">No approved orders waiting for dispatch. Approve an order first.</p>
        )}
        {error && <div className="text-bad text-sm mt-3">{error}</div>}

        {result && (
          <div className="bg-surface-2 rounded p-4 mt-4 space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-ink-muted text-xs">Tanker</div>
                <div className="data-num text-ink-primary">{result.recommended_tanker}</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Driver</div>
                <div className="text-ink-primary">{result.recommended_driver}</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Departure</div>
                <div className="data-num text-ink-primary">{new Date(result.departure_time).toLocaleTimeString()}</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">ETA</div>
                <div className="data-num text-ink-primary">{new Date(result.eta).toLocaleTimeString()}</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Estimated cost</div>
                <div className="data-num text-ink-primary">₹{result.estimated_cost.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-ink-muted text-xs">Risk</div>
                <StatusBadge status={result.risk_level} />
              </div>
              <div>
                <div className="text-ink-muted text-xs">Iterations run</div>
                <div className="data-num text-ink-primary">{result.iterations_run}</div>
              </div>
            </div>
            <p className="text-ink-secondary text-xs leading-relaxed border-t border-line pt-3">{result.explanation}</p>
          </div>
        )}
      </div>

      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Dispatches</div>
        <div className="space-y-2">
          {dispatches.length === 0 && <div className="text-ink-muted text-sm">No dispatches yet.</div>}
          {dispatches.map((d) => (
            <div key={d.id} className="flex items-center justify-between py-2 border-b border-line last:border-0 text-sm">
              <div>
                <div className="text-ink-primary">Dispatch #{d.id} — Order #{d.order_id}</div>
                <div className="text-ink-muted text-xs">
                  {d.distance_km} km · ₹{d.estimated_cost?.toLocaleString()}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={d.risk_level || 'NORMAL'} />
                <span className="text-ink-secondary text-xs">{d.status}</span>
                {d.status === 'PLANNED' && (
                  <button onClick={() => approve(d.id)} disabled={busy} className="text-xs border border-line rounded px-2 py-1 hover:border-line-strong disabled:opacity-50">
                    Approve
                  </button>
                )}
                {d.status === 'ACTIVE' && (
                  <button onClick={() => complete(d.id)} disabled={busy} className="text-xs border border-line rounded px-2 py-1 hover:border-line-strong disabled:opacity-50">
                    Mark delivered
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
