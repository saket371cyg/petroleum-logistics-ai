import React, { useEffect, useState } from 'react'
import { fleetApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'

export default function Fleet() {
  const { user } = useAuth()
  const [tankers, setTankers] = useState([])
  const [drivers, setDrivers] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Tanker Modal State
  const [tankerModalOpen, setTankerModalOpen] = useState(false)
  const [editingTanker, setEditingTanker] = useState(null)
  const [tankerForm, setTankerForm] = useState({
    code: '',
    capacity_l: '20000',
    status: 'AVAILABLE',
    mileage_km: '15000',
    age_years: '2.0',
    current_location: 'Station Depot',
  })

  // Driver Modal State
  const [driverModalOpen, setDriverModalOpen] = useState(false)
  const [editingDriver, setEditingDriver] = useState(null)
  const [driverForm, setDriverForm] = useState({
    name: '',
    license_number: '',
    license_expiry: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
    status: 'AVAILABLE',
  })

  const [modalError, setModalError] = useState('')

  const loadData = () => {
    if (!user) return
    Promise.all([fleetApi.tankers(user.dealerId), fleetApi.drivers(user.dealerId)])
      .then(([t, d]) => {
        setTankers(t.data)
        setDrivers(d.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load fleet data'))
  }

  useEffect(() => {
    loadData()
  }, [user])

  // Tanker Actions
  const openAddTanker = () => {
    setEditingTanker(null)
    setTankerForm({
      code: `TK-${Math.floor(100 + Math.random() * 900)}`,
      capacity_l: '20000',
      status: 'AVAILABLE',
      mileage_km: '15000',
      age_years: '2.0',
      current_location: 'Station Depot',
    })
    setModalError('')
    setTankerModalOpen(true)
  }

  const openEditTanker = (t) => {
    setEditingTanker(t)
    setTankerForm({
      code: t.code,
      capacity_l: t.capacity_l.toString(),
      status: t.status,
      mileage_km: t.mileage_km.toString(),
      age_years: t.age_years.toString(),
      current_location: t.current_location || '',
    })
    setModalError('')
    setTankerModalOpen(true)
  }

  const handleSaveTanker = async (e) => {
    e.preventDefault()
    setModalError('')
    setBusy(true)
    try {
      if (editingTanker) {
        await fleetApi.updateTanker(editingTanker.id, {
          capacity_l: parseFloat(tankerForm.capacity_l),
          status: tankerForm.status,
          mileage_km: parseFloat(tankerForm.mileage_km),
          age_years: parseFloat(tankerForm.age_years),
          current_location: tankerForm.current_location,
        })
        setMessage(`Tanker ${editingTanker.code} updated successfully.`)
      } else {
        await fleetApi.createTanker({
          code: tankerForm.code,
          capacity_l: parseFloat(tankerForm.capacity_l),
          status: tankerForm.status,
          mileage_km: parseFloat(tankerForm.mileage_km),
          age_years: parseFloat(tankerForm.age_years),
          current_location: tankerForm.current_location,
        })
        setMessage(`Tanker ${tankerForm.code} registered to fleet.`)
      }
      setTankerModalOpen(false)
      loadData()
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save tanker')
    } finally {
      setBusy(false)
    }
  }

  const handleQuickTankerStatus = async (tanker, newStatus) => {
    setBusy(true)
    try {
      await fleetApi.updateTanker(tanker.id, { status: newStatus })
      setMessage(`Tanker ${tanker.code} status set to ${newStatus}.`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update tanker status')
    } finally {
      setBusy(false)
    }
  }

  const handleDeleteTanker = async (t) => {
    if (!window.confirm(`Are you sure you want to remove tanker ${t.code}?`)) return
    setBusy(true)
    try {
      await fleetApi.deleteTanker(t.id)
      setMessage(`Tanker ${t.code} removed from fleet.`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete tanker')
    } finally {
      setBusy(false)
    }
  }

  // Driver Actions
  const openAddDriver = () => {
    setEditingDriver(null)
    setDriverForm({
      name: '',
      license_number: `DL-IND-${Math.floor(1000 + Math.random() * 9000)}`,
      license_expiry: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
      status: 'AVAILABLE',
    })
    setModalError('')
    setDriverModalOpen(true)
  }

  const openEditDriver = (d) => {
    setEditingDriver(d)
    setDriverForm({
      name: d.name,
      license_number: d.license_number,
      license_expiry: d.license_expiry,
      status: d.status,
    })
    setModalError('')
    setDriverModalOpen(true)
  }

  const handleSaveDriver = async (e) => {
    e.preventDefault()
    setModalError('')
    setBusy(true)
    try {
      if (editingDriver) {
        await fleetApi.updateDriver(editingDriver.id, {
          name: driverForm.name,
          license_number: driverForm.license_number,
          license_expiry: driverForm.license_expiry,
          status: driverForm.status,
        })
        setMessage(`Driver ${driverForm.name} updated successfully.`)
      } else {
        await fleetApi.createDriver({
          name: driverForm.name,
          license_number: driverForm.license_number,
          license_expiry: driverForm.license_expiry,
          status: driverForm.status,
        })
        setMessage(`Driver ${driverForm.name} added successfully.`)
      }
      setDriverModalOpen(false)
      loadData()
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save driver')
    } finally {
      setBusy(false)
    }
  }

  const handleQuickDriverStatus = async (driver, newStatus) => {
    setBusy(true)
    try {
      await fleetApi.updateDriver(driver.id, { status: newStatus })
      setMessage(`Driver ${driver.name} status updated to ${newStatus}.`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update driver status')
    } finally {
      setBusy(false)
    }
  }

  const handleDeleteDriver = async (d) => {
    if (!window.confirm(`Are you sure you want to remove driver ${d.name}?`)) return
    setBusy(true)
    try {
      await fleetApi.deleteDriver(d.id)
      setMessage(`Driver ${d.name} removed.`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete driver')
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

      {/* Tankers Section */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium">
              Fleet Tankers ({tankers.length})
            </div>
            <p className="text-ink-muted text-xs mt-0.5">
              Available road tankers used for refinery fuel loading & dispatch
            </p>
          </div>
          <button
            onClick={openAddTanker}
            className="bg-amber text-canvas text-xs font-semibold px-3.5 py-2 rounded hover:opacity-90 transition-opacity flex items-center gap-1.5"
          >
            <span>+</span>
            <span>Add Tanker</span>
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-3.5">
          {tankers.map((t) => (
            <div
              key={t.id}
              className="bg-surface-2 border border-line hover:border-line-strong rounded p-4 flex flex-col justify-between transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-ink-primary text-base font-semibold flex items-center gap-2">
                    {t.code}
                    <span className="text-xs text-ink-muted font-normal">#{t.id}</span>
                  </div>
                  <div className="text-ink-secondary text-xs mt-1 space-x-2">
                    <span className="data-num font-medium text-ink-primary">
                      {t.capacity_l.toLocaleString()} L
                    </span>
                    <span>·</span>
                    <span className="data-num">{t.mileage_km.toLocaleString()} km</span>
                    <span>·</span>
                    <span>{t.age_years} yrs</span>
                  </div>
                  {t.current_location && (
                    <div className="text-ink-muted text-[11px] mt-1">📍 {t.current_location}</div>
                  )}
                </div>
                <StatusBadge
                  status={
                    t.status === 'AVAILABLE'
                      ? 'NORMAL'
                      : t.status === 'MAINTENANCE'
                      ? 'CRITICAL'
                      : 'WARNING'
                  }
                />
              </div>

              {/* Tanker Action Controls */}
              <div className="flex items-center justify-between border-t border-line mt-3 pt-2.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-ink-muted text-[11px]">Quick status:</span>
                  <select
                    value={t.status}
                    onChange={(e) => handleQuickTankerStatus(t, e.target.value)}
                    className="bg-surface border border-line rounded px-2 py-1 text-[11px] text-ink-primary focus:outline-none"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OUT_OF_SERVICE">OUT_OF_SERVICE</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditTanker(t)}
                    className="text-ink-secondary hover:text-ink-primary px-2 py-1 rounded bg-surface border border-line hover:border-line-strong"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDeleteTanker(t)}
                    className="text-bad hover:underline px-1 py-1"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {tankers.length === 0 && (
            <div className="text-ink-muted text-sm col-span-2 py-4">No tankers in fleet.</div>
          )}
        </div>
      </div>

      {/* Drivers Section */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium">
              Registered Drivers ({drivers.length})
            </div>
            <p className="text-ink-muted text-xs mt-0.5">
              Commercial hazardous goods licensed drivers
            </p>
          </div>
          <button
            onClick={openAddDriver}
            className="bg-amber text-canvas text-xs font-semibold px-3.5 py-2 rounded hover:opacity-90 transition-opacity flex items-center gap-1.5"
          >
            <span>+</span>
            <span>Add Driver</span>
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-3.5">
          {drivers.map((d) => (
            <div
              key={d.id}
              className="bg-surface-2 border border-line hover:border-line-strong rounded p-4 flex flex-col justify-between transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-ink-primary text-base font-semibold flex items-center gap-2">
                    {d.name}
                    <span className="text-xs text-ink-muted font-normal">#{d.id}</span>
                  </div>
                  <div className="text-ink-secondary text-xs mt-1">
                    Lic: <span className="data-num text-ink-primary">{d.license_number}</span>
                  </div>
                  <div className="text-ink-muted text-[11px] mt-0.5">
                    License Expiry:{' '}
                    <span
                      className={`font-medium ${
                        new Date(d.license_expiry) < new Date() ? 'text-bad' : 'text-ink-secondary'
                      }`}
                    >
                      {d.license_expiry}
                    </span>
                  </div>
                </div>
                <StatusBadge status={d.status === 'AVAILABLE' ? 'NORMAL' : 'WARNING'} />
              </div>

              {/* Driver Action Controls */}
              <div className="flex items-center justify-between border-t border-line mt-3 pt-2.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-ink-muted text-[11px]">Status:</span>
                  <select
                    value={d.status}
                    onChange={(e) => handleQuickDriverStatus(d, e.target.value)}
                    className="bg-surface border border-line rounded px-2 py-1 text-[11px] text-ink-primary focus:outline-none"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="ON_DUTY">ON_DUTY</option>
                    <option value="OFF">OFF</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEditDriver(d)}
                    className="text-ink-secondary hover:text-ink-primary px-2 py-1 rounded bg-surface border border-line hover:border-line-strong"
                  >
                    Edit / Renew
                  </button>
                  <button
                    onClick={() => handleDeleteDriver(d)}
                    className="text-bad hover:underline px-1 py-1"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          {drivers.length === 0 && (
            <div className="text-ink-muted text-sm col-span-2 py-4">No registered drivers.</div>
          )}
        </div>
      </div>

      {/* Tanker Add/Edit Modal */}
      {tankerModalOpen && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <h3 className="text-ink-primary font-semibold text-base">
                {editingTanker ? `Edit Tanker ${editingTanker.code}` : 'Register New Tanker'}
              </h3>
              <button onClick={() => setTankerModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSaveTanker} className="space-y-3.5">
              {!editingTanker && (
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Tanker Code (ID)</label>
                  <input
                    type="text"
                    value={tankerForm.code}
                    onChange={(e) => setTankerForm({ ...tankerForm, code: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    placeholder="e.g. TK-301"
                    required
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Capacity (Liters)</label>
                  <input
                    type="number"
                    value={tankerForm.capacity_l}
                    onChange={(e) => setTankerForm({ ...tankerForm, capacity_l: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Status</label>
                  <select
                    value={tankerForm.status}
                    onChange={(e) => setTankerForm({ ...tankerForm, status: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OUT_OF_SERVICE">OUT_OF_SERVICE</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Odometer (km)</label>
                  <input
                    type="number"
                    value={tankerForm.mileage_km}
                    onChange={(e) => setTankerForm({ ...tankerForm, mileage_km: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Vehicle Age (Years)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={tankerForm.age_years}
                    onChange={(e) => setTankerForm({ ...tankerForm, age_years: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Current Location</label>
                <input
                  type="text"
                  value={tankerForm.current_location}
                  onChange={(e) => setTankerForm({ ...tankerForm, current_location: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  placeholder="e.g. Station Bay 1"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
                <button
                  type="button"
                  onClick={() => setTankerModalOpen(false)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? 'Saving…' : 'Save Tanker'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Driver Add/Edit Modal */}
      {driverModalOpen && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <h3 className="text-ink-primary font-semibold text-base">
                {editingDriver ? `Edit Driver ${editingDriver.name}` : 'Register New Driver'}
              </h3>
              <button onClick={() => setDriverModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSaveDriver} className="space-y-3.5">
              <div>
                <label className="block text-ink-secondary text-xs mb-1">Driver Full Name</label>
                <input
                  type="text"
                  value={driverForm.name}
                  onChange={(e) => setDriverForm({ ...driverForm, name: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  placeholder="e.g. Rajesh Kumar"
                  required
                />
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Commercial License Number</label>
                <input
                  type="text"
                  value={driverForm.license_number}
                  onChange={(e) => setDriverForm({ ...driverForm, license_number: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary data-num focus:border-amber focus:outline-none"
                  placeholder="e.g. DL-04-2023-0091"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">License Expiry Date</label>
                  <input
                    type="date"
                    value={driverForm.license_expiry}
                    onChange={(e) => setDriverForm({ ...driverForm, license_expiry: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Duty Status</label>
                  <select
                    value={driverForm.status}
                    onChange={(e) => setDriverForm({ ...driverForm, status: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="ON_DUTY">ON_DUTY</option>
                    <option value="OFF">OFF</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
                <button
                  type="button"
                  onClick={() => setDriverModalOpen(false)}
                  className="px-4 py-2 text-xs rounded border border-line text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="bg-amber text-canvas text-xs font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50"
                >
                  {busy ? 'Saving…' : 'Save Driver'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
