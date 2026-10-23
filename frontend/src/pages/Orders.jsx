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
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Custom order form state
  const [customFuelType, setCustomFuelType] = useState('DIESEL')
  const [customQty, setCustomQty] = useState('12000')

  const loadOrders = () => {
    if (!user) return
    ordersApi
      .list(user.dealerId)
      .then((res) => setOrders(res.data))
      .catch(() => {})
  }

  useEffect(loadOrders, [user])

  const getRecommendation = async () => {
    setError('')
    setMessage('')
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
    setError('')
    setMessage('')
    try {
      await ordersApi.create(recommendation.fuel_type, recommendation.recommended_quantity_l)
      setMessage(`AI order for ${recommendation.recommended_quantity_l.toLocaleString()} L of ${recommendation.fuel_type} created!`)
      setRecommendation(null)
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create order')
    } finally {
      setBusy(false)
    }
  }

  const handleCreateCustomOrder = async (e) => {
    e.preventDefault()
    const qty = parseFloat(customQty)
    if (isNaN(qty) || qty <= 0) {
      setError('Please specify a positive fuel quantity in liters')
      return
    }
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await ordersApi.create(customFuelType, qty)
      setMessage(`Custom order for ${qty.toLocaleString()} L of ${customFuelType} created successfully.`)
      setCustomQty('12000')
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create custom order')
    } finally {
      setBusy(false)
    }
  }

  const approve = async (orderId) => {
    setBusy(true)
    setError('')
    try {
      await ordersApi.approve(orderId)
      setMessage(`Order #${orderId} approved and is ready for dispatch optimization!`)
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to approve order')
    } finally {
      setBusy(false)
    }
  }

  const cancel = async (orderId) => {
    setBusy(true)
    setError('')
    try {
      await ordersApi.cancel(orderId)
      setMessage(`Order #${orderId} cancelled.`)
      loadOrders()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to cancel order')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      {message && (
        <div className="bg-good-soft border border-good text-good text-sm p-3 rounded flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="text-xs text-good hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {error && <div className="text-bad text-sm p-3 bg-bad-soft border border-bad rounded">{error}</div>}

      {/* Grid: AI Recommendation on left/top, Custom Order on right */}
      <div className="grid md:grid-cols-2 gap-5">
        {/* AI Recommendation Card */}
        <div className="card p-5 flex flex-col justify-between">
          <div>
            <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-1">
              AI Automated Order Recommendation
            </div>
            <p className="text-ink-muted text-xs mb-3">
              Calculates lead-time demand, stockout risk, and optimal order size.
            </p>
            <div className="flex gap-2 mb-3">
              {['DIESEL', 'PETROL'].map((ft) => (
                <button
                  key={ft}
                  onClick={() => setFuelType(ft)}
                  className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                    fuelType === ft
                      ? 'bg-amber text-canvas border-amber font-semibold'
                      : 'border-line text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  {ft}
                </button>
              ))}
              <button
                onClick={getRecommendation}
                className="px-3.5 py-1.5 text-xs font-medium rounded border border-line bg-surface-2 hover:bg-surface-3 text-ink-primary hover:border-line-strong transition-colors"
              >
                Analyze & Recommend
              </button>
            </div>

            {recommendation && (
              <div className="bg-surface-2 border border-line rounded p-4 space-y-2 mt-2">
                <div className="flex items-center justify-between">
                  <span className="text-ink-primary text-sm font-semibold">
                    {recommendation.should_order ? 'Order Recommended' : 'Adequate Coverage'}
                  </span>
                  <span className="data-num text-amber text-lg font-bold">
                    {recommendation.recommended_quantity_l.toLocaleString()} L
                  </span>
                </div>
                <p className="text-ink-secondary text-xs leading-relaxed">{recommendation.explanation}</p>
                {recommendation.should_order && (
                  <button
                    onClick={createFromRecommendation}
                    disabled={busy}
                    className="mt-2 bg-amber text-canvas text-xs font-semibold rounded px-4 py-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    Create AI Recommended Order
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Custom Manual Order Card */}
        <div className="card p-5">
          <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-1">
            Manual / Custom Order Creation
          </div>
          <p className="text-ink-muted text-xs mb-3">
            Place custom procurement orders anytime based on emergency or bulk dealer requirements.
          </p>

          <form onSubmit={handleCreateCustomOrder} className="space-y-3.5">
            <div>
              <label className="block text-ink-secondary text-xs mb-1">Fuel Type</label>
              <select
                value={customFuelType}
                onChange={(e) => setCustomFuelType(e.target.value)}
                className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
              >
                <option value="DIESEL">DIESEL</option>
                <option value="PETROL">PETROL</option>
                <option value="PREMIUM PETROL">PREMIUM PETROL</option>
              </select>
            </div>

            <div>
              <label className="block text-ink-secondary text-xs mb-1">Order Quantity (Liters)</label>
              <input
                type="number"
                step="500"
                value={customQty}
                onChange={(e) => setCustomQty(e.target.value)}
                className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                placeholder="e.g. 15000"
                required
              />
            </div>

            <div className="flex gap-2">
              {[8000, 12000, 20000].map((preset) => (
                <button
                  type="button"
                  key={preset}
                  onClick={() => setCustomQty(preset.toString())}
                  className="text-xs bg-surface-2 border border-line text-ink-secondary px-2.5 py-1 rounded hover:text-ink-primary"
                >
                  +{preset.toLocaleString()} L
                </button>
              ))}
            </div>

            <button
              type="submit"
              disabled={busy}
              className="w-full mt-2 bg-surface-2 hover:bg-surface-3 border border-line hover:border-line-strong text-ink-primary text-xs font-semibold py-2 rounded transition-colors disabled:opacity-50"
            >
              {busy ? 'Submitting…' : 'Submit Manual Order'}
            </button>
          </form>
        </div>
      </div>

      {/* Order History */}
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-3">
          Fuel Order History ({orders.length})
        </div>
        <div className="space-y-2.5">
          {orders.length === 0 && <div className="text-ink-muted text-sm py-3">No orders placed yet.</div>}
          {orders.map((o) => (
            <div
              key={o.id}
              className="flex flex-col md:flex-row md:items-center justify-between p-3 rounded bg-surface-2 border border-line hover:border-line-strong transition-colors gap-2 text-sm"
            >
              <div>
                <div className="text-ink-primary font-medium flex items-center gap-2">
                  <span>Order #{o.id}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-surface border border-line text-ink-secondary font-normal">
                    {o.fuel_type}
                  </span>
                  <span className="data-num font-semibold text-ink-primary">
                    {o.quantity_l.toLocaleString()} L
                  </span>
                  {o.recommended_by_agent && (
                    <span className="text-[10px] bg-amber/10 border border-amber text-amber px-1.5 py-0.2 rounded font-medium">
                      AI Generated
                    </span>
                  )}
                </div>
                <div className="text-ink-muted text-xs mt-0.5">
                  Created {new Date(o.created_at).toLocaleString()}
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <StatusBadge status={o.status} />

                {o.status === 'PENDING' && (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => approve(o.id)}
                      disabled={busy}
                      className="text-xs bg-amber text-canvas font-medium rounded px-3 py-1 hover:opacity-90 disabled:opacity-50 transition-opacity"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => cancel(o.id)}
                      disabled={busy}
                      className="text-xs border border-bad text-bad hover:bg-bad-soft rounded px-2.5 py-1 disabled:opacity-50 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
