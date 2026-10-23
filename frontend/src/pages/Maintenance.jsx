import React, { useEffect, useState } from 'react'
import { maintenanceApi, fleetApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Maintenance() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [tankers, setTankers] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Maintenance Service Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedTanker, setSelectedTanker] = useState(null)
  const [serviceForm, setServiceForm] = useState({
    tanker_id: '',
    service_date: new Date().toISOString().split('T')[0],
    mileage_at_service: '',
    issue_notes: 'Routine 10,000 km periodic inspection, oil & filter replacement, brake pads tested.',
    next_due_date: new Date(Date.now() + 180 * 24 * 3600 * 1000).toISOString().split('T')[0],
  })
  const [modalError, setModalError] = useState('')

  const loadData = () => {
    if (!user) return
    Promise.all([maintenanceApi.alerts(user.dealerId), fleetApi.tankers(user.dealerId)])
      .then(([a, t]) => {
        setAlerts(a.data)
        setTankers(t.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load maintenance data'))
  }

  useEffect(() => {
    loadData()
  }, [user])

  const openServiceModal = (tankerId = null) => {
    setModalError('')
    const t = tankerId ? tankers.find((item) => item.id === tankerId) : tankers[0]
    setSelectedTanker(t || null)
    setServiceForm({
      tanker_id: t ? t.id.toString() : '',
      service_date: new Date().toISOString().split('T')[0],
      mileage_at_service: t ? t.mileage_km.toString() : '20000',
      issue_notes: 'Routine periodic inspection, oil & filter change, brake test and tire inspection.',
      next_due_date: new Date(Date.now() + 180 * 24 * 3600 * 1000).toISOString().split('T')[0],
    })
    setModalOpen(true)
  }

  const handleLogService = async (e) => {
    e.preventDefault()
    setModalError('')
    setBusy(true)
    try {
      const res = await maintenanceApi.log({
        tanker_id: parseInt(serviceForm.tanker_id),
        service_date: serviceForm.service_date,
        mileage_at_service: parseFloat(serviceForm.mileage_at_service),
        issue_notes: serviceForm.issue_notes,
        next_due_date: serviceForm.next_due_date,
      })
      setMessage(res.data.message || 'Maintenance recorded successfully! Tanker risk cleared.')
      setModalOpen(false)
      loadData()
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to record maintenance service')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Banner */}
      <div className="card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div>
          <h2 className="text-ink-primary font-medium text-base">Tanker Predictive Maintenance Intelligence</h2>
          <p className="text-ink-secondary text-xs mt-0.5">
            Rule-based risk scoring (mileage since service, elapsed days, vehicle age, breakdown history).
          </p>
        </div>
        <button
          onClick={() => openServiceModal()}
          className="bg-amber text-canvas text-xs font-semibold px-3.5 py-2 rounded hover:opacity-90 transition-opacity flex items-center gap-1.5"
        >
          <span>🔧</span>
          <span>Log Maintenance Service</span>
        </button>
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

      {/* Maintenance Risk Alerts */}
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-3">
          Vehicle Maintenance Risk Scores ({alerts.length})
        </div>

        <div className="space-y-3">
          {alerts.map((a) => (
            <div
              key={a.tanker_id}
              className="p-4 rounded bg-surface-2 border border-line hover:border-line-strong transition-colors"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="text-ink-primary font-semibold text-base">{a.tanker_code}</span>
                  <StatusBadge status={a.risk_level} />
                  <span className="data-num text-xs text-ink-muted">Tanker ID #{a.tanker_id}</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-ink-muted text-xs mr-1.5">Risk Score:</span>
                    <span
                      className={`data-num text-sm font-semibold ${
                        a.risk_score >= 70
                          ? 'text-bad'
                          : a.risk_score >= 40
                          ? 'text-warn'
                          : 'text-good'
                      }`}
                    >
                      {a.risk_score} / 100
                    </span>
                  </div>
                  <button
                    onClick={() => openServiceModal(a.tanker_id)}
                    className="bg-surface hover:bg-surface-3 text-ink-primary border border-line hover:border-line-strong text-xs font-medium px-3 py-1.5 rounded transition-colors flex items-center gap-1"
                  >
                    <span>🛠️</span>
                    <span>Service Tanker</span>
                  </button>
                </div>
              </div>

              <p className="text-ink-secondary text-xs mt-2 leading-relaxed">{a.reason}</p>

              <div className="flex items-center gap-4 text-ink-muted text-[11px] mt-2 pt-2 border-t border-line">
                <div>
                  Recommended Service By:{' '}
                  <span className="text-ink-primary font-medium">{a.recommended_service_date}</span>
                </div>
                <div>
                  Safe for Dispatch:{' '}
                  <span
                    className={`font-semibold ${
                      a.risk_level === 'HIGH' ? 'text-bad' : 'text-good'
                    }`}
                  >
                    {a.risk_level === 'HIGH' ? '❌ NO (Needs Service)' : '✅ YES'}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {alerts.length === 0 && (
            <div className="text-ink-muted text-sm py-4">All tankers currently in good operating health.</div>
          )}
        </div>
      </div>

      {/* Log Maintenance Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <div>
                <h3 className="text-ink-primary font-semibold text-base">Log Vehicle Service & Inspection</h3>
                <p className="text-ink-muted text-xs">Resets maintenance risk scoring and verifies vehicle health.</p>
              </div>
              <button onClick={() => setModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {modalError}
              </div>
            )}

            <form onSubmit={handleLogService} className="space-y-3.5">
              <div>
                <label className="block text-ink-secondary text-xs mb-1">Select Tanker</label>
                <select
                  value={serviceForm.tanker_id}
                  onChange={(e) => {
                    const id = e.target.value
                    const t = tankers.find((item) => item.id.toString() === id)
                    setSelectedTanker(t || null)
                    setServiceForm({
                      ...serviceForm,
                      tanker_id: id,
                      mileage_at_service: t ? t.mileage_km.toString() : serviceForm.mileage_at_service,
                    })
                  }}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  required
                >
                  <option value="">Select a tanker…</option>
                  {tankers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} — {t.capacity_l.toLocaleString()} L ({t.mileage_km.toLocaleString()} km)
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Service Date</label>
                  <input
                    type="date"
                    value={serviceForm.service_date}
                    onChange={(e) => setServiceForm({ ...serviceForm, service_date: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Current Odometer (km)</label>
                  <input
                    type="number"
                    value={serviceForm.mileage_at_service}
                    onChange={(e) => setServiceForm({ ...serviceForm, mileage_at_service: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Service Notes / Work Done</label>
                <textarea
                  rows="3"
                  value={serviceForm.issue_notes}
                  onChange={(e) => setServiceForm({ ...serviceForm, issue_notes: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  placeholder="e.g. Oil change, brake pad replacement, dip calibration"
                  required
                />
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Next Service Due Date</label>
                <input
                  type="date"
                  value={serviceForm.next_due_date}
                  onChange={(e) => setServiceForm({ ...serviceForm, next_due_date: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? 'Recording…' : 'Record Service & Clear Risk'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
