import React, { useEffect, useState } from 'react'
import { refineryApi } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function RefinerySlots() {
  const [slots, setSlots] = useState([])
  const [refineries, setRefineries] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  // Add Slot Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [slotForm, setSlotForm] = useState({
    refinery_id: '',
    slot_date: new Date().toISOString().split('T')[0],
    slot_time: '10:00',
    duration_hours: '2',
  })
  const [modalError, setModalError] = useState('')

  const loadData = () => {
    Promise.all([refineryApi.slots(), refineryApi.refineries()])
      .then(([s, r]) => {
        setSlots(s.data)
        setRefineries(r.data)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load refinery slots'))
  }

  useEffect(() => {
    loadData()
  }, [])

  const openAddSlot = () => {
    setModalError('')
    setSlotForm({
      refinery_id: refineries[0]?.id?.toString() || '1',
      slot_date: new Date().toISOString().split('T')[0],
      slot_time: '14:00',
      duration_hours: '2',
    })
    setModalOpen(true)
  }

  const handleCreateSlot = async (e) => {
    e.preventDefault()
    setModalError('')
    setBusy(true)

    try {
      const startIso = `${slotForm.slot_date}T${slotForm.slot_time}:00`
      const startDate = new Date(startIso)
      const endDate = new Date(startDate.getTime() + parseFloat(slotForm.duration_hours) * 3600 * 1000)

      await refineryApi.createSlot({
        refinery_id: parseInt(slotForm.refinery_id),
        slot_start: startDate.toISOString(),
        slot_end: endDate.toISOString(),
        status: 'OPEN',
      })
      setMessage('Refinery loading slot added to OMC schedule.')
      setModalOpen(false)
      loadData()
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to create refinery loading slot')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Banner */}
      <div className="card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div>
          <h2 className="text-ink-primary font-medium text-base">Terminal Loading Slots & Refinery Hubs</h2>
          <p className="text-ink-secondary text-xs mt-0.5">
            Coordinate tanker gantries with OMC terminal gates (Jamnagar, Koyali, Indore, Bhopal).
          </p>
        </div>
        <button
          onClick={openAddSlot}
          className="bg-amber text-canvas text-xs font-semibold px-3.5 py-2 rounded hover:opacity-90 transition-opacity flex items-center gap-1.5"
        >
          <span>+</span>
          <span>Add Loading Slot</span>
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

      {/* Refineries Overview */}
      {refineries.length > 0 && (
        <div className="grid md:grid-cols-2 gap-3.5">
          {refineries.map((r) => (
            <div key={r.id} className="card p-4 bg-surface flex items-center justify-between">
              <div>
                <div className="text-ink-primary font-medium text-sm flex items-center gap-2">
                  <span>🏢 {r.name}</span>
                  <span className="text-xs text-ink-muted">#{r.id}</span>
                </div>
                <div className="text-ink-muted text-xs mt-1">📍 {r.location}</div>
              </div>
              <div className="text-right">
                <span className="data-num text-xs font-medium text-ink-secondary">
                  ~{r.distance_km_default} km
                </span>
                <span className="block text-[10px] text-ink-muted">Default transit</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Open Loading Slots List */}
      <div className="card p-5">
        <div className="text-ink-secondary text-xs uppercase tracking-wide font-medium mb-3">
          Available Terminal Loading Bays ({slots.length})
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {slots.map((s) => (
            <div
              key={s.id}
              className="bg-surface-2 border border-line hover:border-line-strong rounded p-3.5 flex flex-col justify-between transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-ink-primary text-sm font-semibold flex items-center gap-1.5">
                    <span>Bay #{s.id}</span>
                    <span className="text-xs font-normal text-ink-secondary">
                      ({s.refinery_name || `Hub #${s.refinery_id}`})
                    </span>
                  </div>
                  {s.refinery_location && (
                    <div className="text-ink-muted text-[11px] mt-0.5">📍 {s.refinery_location}</div>
                  )}
                  <div className="text-ink-secondary text-xs mt-2 space-y-0.5">
                    <div>
                      Start:{' '}
                      <span className="data-num text-ink-primary">
                        {new Date(s.slot_start).toLocaleDateString()}{' '}
                        {new Date(s.slot_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div>
                      End:{' '}
                      <span className="data-num text-ink-primary">
                        {new Date(s.slot_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </div>
                <StatusBadge status={s.status === 'OPEN' ? 'NORMAL' : 'WARNING'} />
              </div>
            </div>
          ))}

          {slots.length === 0 && (
            <div className="text-ink-muted text-sm py-4 col-span-3">No active loading slots available.</div>
          )}
        </div>
      </div>

      {/* Add Slot Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 bg-surface border-line-strong shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-line mb-4">
              <h3 className="text-ink-primary font-semibold text-base">Add Refinery Loading Slot</h3>
              <button onClick={() => setModalOpen(false)} className="text-ink-muted hover:text-ink-primary">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="text-bad text-xs p-2.5 bg-bad-soft border border-bad rounded mb-3">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateSlot} className="space-y-3.5">
              <div>
                <label className="block text-ink-secondary text-xs mb-1">Terminal / Refinery Hub</label>
                <select
                  value={slotForm.refinery_id}
                  onChange={(e) => setSlotForm({ ...slotForm, refinery_id: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                  required
                >
                  {refineries.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.location})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Slot Date</label>
                  <input
                    type="date"
                    value={slotForm.slot_date}
                    onChange={(e) => setSlotForm({ ...slotForm, slot_date: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-ink-secondary text-xs mb-1">Start Time</label>
                  <input
                    type="time"
                    value={slotForm.slot_time}
                    onChange={(e) => setSlotForm({ ...slotForm, slot_time: e.target.value })}
                    className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary text-xs mb-1">Slot Duration (Hours)</label>
                <select
                  value={slotForm.duration_hours}
                  onChange={(e) => setSlotForm({ ...slotForm, duration_hours: e.target.value })}
                  className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:border-amber focus:outline-none"
                >
                  <option value="1">1 Hour</option>
                  <option value="2">2 Hours</option>
                  <option value="3">3 Hours</option>
                  <option value="4">4 Hours</option>
                </select>
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
                  {busy ? 'Saving…' : 'Add Slot'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
