import React, { useEffect, useState } from 'react'
import { refineryApi } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function RefinerySlots() {
  const [slots, setSlots] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    refineryApi.slots().then((res) => setSlots(res.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load slots'))
  }, [])

  if (error) return <div className="text-bad text-sm">{error}</div>

  return (
    <div className="card p-5">
      <div className="text-ink-secondary text-xs uppercase tracking-wide mb-3">Open refinery loading slots</div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {slots.map((s) => (
          <div key={s.id} className="bg-surface-2 rounded p-3 flex items-center justify-between">
            <div>
              <div className="text-ink-primary text-sm data-num">
                {new Date(s.slot_start).toLocaleString()}
              </div>
              <div className="text-ink-muted text-xs mt-0.5">Refinery #{s.refinery_id}</div>
            </div>
            <StatusBadge status={s.status === 'OPEN' ? 'NORMAL' : 'WARNING'} />
          </div>
        ))}
        {slots.length === 0 && <div className="text-ink-muted text-sm">No open slots.</div>}
      </div>
    </div>
  )
}
