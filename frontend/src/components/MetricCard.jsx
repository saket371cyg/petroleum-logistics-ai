import React from 'react'

export default function MetricCard({ label, value, sublabel, accent }) {
  return (
    <div className="card p-4">
      <div className="text-ink-muted text-xs uppercase tracking-wide">{label}</div>
      <div className={`data-num text-2xl font-medium mt-1 ${accent ? 'text-amber' : 'text-ink-primary'}`}>
        {value}
      </div>
      {sublabel && <div className="text-ink-secondary text-xs mt-1">{sublabel}</div>}
    </div>
  )
}
