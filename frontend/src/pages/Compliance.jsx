import React, { useEffect, useState } from 'react'
import { complianceApi, fleetApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Compliance() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [tankers, setTankers] = useState([])
  const [drivers, setDrivers] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Renew Modal
  const [renewModalOpen, setRenewModalOpen] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [newExpiryDate, setNewExpiryDate] = useState('')
  const [renewError, setRenewError] = useState('')

  // Add Document Modal
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addForm, setAddForm] = useState({
    entity_type: 'TANKER',
    entity_id: '',
    doc_type: 'PESO_PERMIT',
    expiry_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
  })
  const [addError, setAddError] = useState('')

  const loadData = () => {
    if (!user) return
    Promise.all([
      complianceApi.alerts(user.dealerId),
      fleetApi.tankers(user.dealerId),
      fleetApi.drivers(user.dealerId),
    ])
      .then(([c, t, d]) => {
        setAlerts(c.data)
        setTankers(t.data)
        setDrivers(d.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load compliance data'))
  }

  useEffect(() => {
    loadData()
  }, [user])

  const openRenewModal = (alert) => {
    setSelectedAlert(alert)
    setRenewError('')
    // Default to +1 year from today
    setNewExpiryDate(new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0])
    setRenewModalOpen(true)
  }

  const handleRenew = async (e) => {
    e.preventDefault()
    setRenewError('')
    setBusy(true)
    try {
      const res = await complianceApi.renew({
        entity_type: selectedAlert.entity_type,
        entity_id: selectedAlert.entity_id,
        doc_type: selectedAlert.doc_type,
        new_expiry_date: newExpiryDate,
      })
      setMessage(res.data.message || 'Document renewed successfully! Compliance alert cleared.')
      setRenewModalOpen(false)
      loadData()
    } catch (err) {
      setRenewError(err.response?.data?.detail || 'Failed to renew document')
    } finally {
      setBusy(false)
    }
  }

  const openAddModal = () => {
    setAddError('')
    setAddForm({
      entity_type: 'TANKER',
      entity_id: tankers[0]?.id?.toString() || '',
      doc_type: 'PESO_PERMIT',
      expiry_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
    })
    setAddModalOpen(true)
  }

  const handleAddDocument = async (e) => {
    e.preventDefault()
    setAddError('')
    setBusy(true)
    try {
      await complianceApi.create({
        entity_type: addForm.entity_type,
        entity_id: parseInt(addForm.entity_id),
        doc_type: addForm.doc_type,
        expiry_date: addForm.expiry_date,
      })
      setMessage('Compliance document registered successfully.')
      setAddModalOpen(false)
      loadData()
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to add compliance document')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Banner */}
      <div className="card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div>
          <h2 className="text-ink-primary font-medium text-base">Regulatory & Safety Compliance</h2>
          <p className="text-ink-secondary text-xs mt-0.5">
            Deterministic rule-based checks for PESO licenses, driver commercial permits, and tanker certifications.
          </p>
        </div>
        <button
          onClick={openAddModal}
          className="bg-amber text-canvas text-xs font-semibold px-3.5 py-2 rounded hover:opacity-90 transition-opacity flex items-center gap-1.5"
        >
          <span>+</span>
          <span>Add Certificate</span>
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

      {/* Compliance Alerts Table */}
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-3">
          Compliance Document Status ({alerts.length})
        </div>

        {alerts.length === 0 ? (
          <div className="text-ink-muted text-sm py-4">
            ✅ No expired or expiring compliance documents. All tankers and drivers are fully certified.
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((a, i) => (
              <div
                key={i}
                className="flex flex-col md:flex-row md:items-center justify-between p-3.5 rounded bg-surface-2 border border-line hover:border-line-strong transition-colors gap-3"
              >
                <div>
                  <div className="text-ink-primary font-medium text-sm flex items-center gap-2">
                    {a.entity_label}
                    <span className="text-xs text-ink-muted">({a.entity_type})</span>
                  </div>
                  <div className="text-ink-secondary text-xs mt-1">
                    Document:{' '}
                    <span className="font-semibold text-ink-primary">{a.doc_type}</span> · Expiry Date:{' '}
                    <span
                      className={`font-medium ${
                        a.status === 'EXPIRED' ? 'text-bad' : 'text-warn'
                      }`}
                    >
                      {a.expiry_date}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="data-num text-xs font-medium text-ink-secondary block">
                      {a.days_to_expiry < 0
                        ? `${Math.abs(a.days_to_expiry)} days overdue`
                        : `${a.days_to_expiry} days remaining`}
                    </span>
                    <StatusBadge status={a.status} />
                  </div>
                  <button
                    onClick={() => openRenewModal(a)}
                    className="bg-surface hover:bg-surface-3 text-ink-primary border border-line hover:border-line-strong text-xs font-medium px-3 py-1.5 rounded transition-colors flex items-center gap-1"
                  >
                    <span>🔄</span>
                    <span>Renew Document</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Renew Modal */}
      {renewModalOpen && selectedAlert && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <div>
                <h3 className="text-ink-primary font-semibold text-base">Renew Compliance Certificate</h3>
                <p className="text-ink-muted text-xs">
                  {selectedAlert.entity_label} · {selectedAlert.doc_type}
                </p>
              </div>
              <button onClick={() => setRenewModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {renewError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {renewError}
              </div>
            )}

            <form onSubmit={handleRenew} className="space-y-4">
              <div>
                <label className="block text-ink-secondary text-xs mb-1">Current Expiry Date</label>
                <div className="text-sm font-semibold text-bad data-num">{selectedAlert.expiry_date}</div>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">New Expiration Date</label>
                <input
                  type="date"
                  value={newExpiryDate}
                  onChange={(e) => setNewExpiryDate(e.target.value)}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
                <button
                  type="button"
                  onClick={() => setRenewModalOpen(false)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? 'Saving…' : 'Save & Clear Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Certificate Modal */}
      {addModalOpen && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <h3 className="text-ink-primary font-semibold text-base">Register Compliance Document</h3>
              <button onClick={() => setAddModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {addError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {addError}
              </div>
            )}

            <form onSubmit={handleAddDocument} className="space-y-3.5">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Entity Type</label>
                  <select
                    value={addForm.entity_type}
                    onChange={(e) => {
                      const type = e.target.value
                      setAddForm({
                        ...addForm,
                        entity_type: type,
                        entity_id: type === 'TANKER' ? tankers[0]?.id?.toString() || '' : drivers[0]?.id?.toString() || '',
                      })
                    }}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  >
                    <option value="TANKER">Tanker</option>
                    <option value="DRIVER">Driver</option>
                  </select>
                </div>

                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Select Entity</label>
                  <select
                    value={addForm.entity_id}
                    onChange={(e) => setAddForm({ ...addForm, entity_id: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    required
                  >
                    {addForm.entity_type === 'TANKER'
                      ? tankers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.code}
                          </option>
                        ))
                      : drivers.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Document Type</label>
                <select
                  value={addForm.doc_type}
                  onChange={(e) => setAddForm({ ...addForm, doc_type: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                >
                  <option value="PESO_PERMIT">PESO Explosives Permit</option>
                  <option value="INSURANCE">Commercial Vehicle Insurance</option>
                  <option value="CALIBRATION_CERT">Hydrostatic Tank Calibration</option>
                  <option value="PUC_CERT">Pollution Under Control (PUC)</option>
                  <option value="LICENSE">Commercial Driver License</option>
                  <option value="HAZMAT_CERT">Hazardous Materials Endorsement</option>
                </select>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Expiration Date</label>
                <input
                  type="date"
                  value={addForm.expiry_date}
                  onChange={(e) => setAddForm({ ...addForm, expiry_date: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
                <button
                  type="button"
                  onClick={() => setAddModalOpen(false)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? 'Saving…' : 'Add Document'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
