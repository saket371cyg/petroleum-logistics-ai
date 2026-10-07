import React from 'react'

const MAP = {
  NORMAL: 'badge-normal',
  LOW: 'badge-normal',
  VALID: 'badge-normal',
  WARNING: 'badge-warning',
  MEDIUM: 'badge-warning',
  EXPIRING_SOON: 'badge-warning',
  CRITICAL: 'badge-critical',
  HIGH: 'badge-critical',
  EXPIRED: 'badge-critical',
}

export default function StatusBadge({ status }) {
  const cls = MAP[status] || 'badge-neutral'
  return <span className={`badge ${cls}`}>{status}</span>
}
