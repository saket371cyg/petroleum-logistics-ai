import React, { useEffect, useState } from 'react'
import { ordersApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Orders() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [fuelType, setFuelType] = useState('DIESEL')
  const [recommendation, setRecommendation] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const loadOrders = () => {
    if (!user) return
    ordersApi.list(user.dealerId).then((res) => setOrders(res.data)).catch(() => {})
  }

  useEffect(loadOrders, [user])

  const getRecommendation = async () => {
    setError('')
    setRecommendation(null)
    try {
      const res = await ordersApi.recommend(0, fuelType)
      setRecommendation(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to get recommendation')
    }
  }

  const createFromRecommendation = async () => {
    if (!recommendation) return
    setBusy(true)
    try {
      await ordersApi.create(recommendation.fuel_type, recommendation.recommended_quantity_l)
      setRecommendation(null)
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create order')
    } finally {
      setBusy(false)
    }
  }

  const approve = async (orderId) => {
    setBusy(true)
    try {
      await ordersApi.approve(orderId)
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to approve order')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">
          AI order recommendation
        </div>
        <div className="flex gap-2 mb-4">
          {['PETROL', 'DIESEL'].map((ft) => (
            <button
              key={ft}
              onClick={() => setFuelType(ft)}
              className={`px-3 py-1.5 text-sm rounded border ${
                fuelType === ft ? 'bg-amber text-canvas border-amber font-medium' : 'border-line text-ink-secondary'
              }`}
            >
              {ft}
            </button>
          ))}
          <button
            onClick={getRecommendation}
            className="px-3 py-1.5 text-sm rounded border border-line text-ink-primary hover:border-line-strong"
          >
            Get recommendation
          </button>
        </div>

        {error && <div className="text-bad text-sm mb-3">{error}</div>}

        {recommendation && (
          <div className="bg-surface-2 rounded p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-ink-primary text-sm font-medium">
                {recommendation.should_order ? 'Order recommended' : 'No order needed'}
              </span>
              <span className="data-num text-amber text-lg">
                {recommendation.recommended_quantity_l.toLocaleString()} L
              </span>
            </div>
            <p className="text-ink-secondary text-sm leading-relaxed">{recommendation.explanation}</p>
            {recommendation.should_order && (
              <button
                onClick={createFromRecommendation}
                disabled={busy}
                className="mt-2 bg-amber text-canvas text-sm font-medium rounded px-4 py-1.5 hover:opacity-90 disabled:opacity-50"
              >
                Create order
              </button>
            )}
          </div>
        )}
      </div>

      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Order history</div>
        <div className="space-y-2">
          {orders.length === 0 && <div className="text-ink-muted text-sm">No orders yet.</div>}
          {orders.map((o) => (
            <div key={o.id} className="flex items-center justify-between py-2 border-b border-line last:border-0 text-sm">
              <div>
                <div className="text-ink-primary">{o.fuel_type} — {o.quantity_l.toLocaleString()} L</div>
                <div className="text-ink-muted text-xs">{new Date(o.created_at).toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={o.status} />
                {o.status === 'PENDING' && (
                  <button
                    onClick={() => approve(o.id)}
                    disabled={busy}
                    className="text-xs border border-line rounded px-2 py-1 text-ink-primary hover:border-line-strong disabled:opacity-50"
                  >
                    Approve
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
