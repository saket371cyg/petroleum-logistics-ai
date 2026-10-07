import React from 'react'
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/orders', label: 'Orders' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/fleet', label: 'Fleet' },
  { to: '/dispatch', label: 'Dispatch' },
  { to: '/refinery-slots', label: 'Refinery slots' },
  { to: '/compliance', label: 'Compliance' },
  { to: '/maintenance', label: 'Maintenance' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/ai-assistant', label: 'AI assistant' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-surface border-r border-line h-screen sticky top-0 flex flex-col">
      <div className="px-5 py-5 border-b border-line">
        <div className="text-ink-primary font-semibold text-sm tracking-wide">PETRO OPS</div>
        <div className="text-ink-muted text-xs mt-0.5">Decision Intelligence</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-5 py-2 text-sm border-l-2 transition-colors ${
                isActive
                  ? 'border-amber text-ink-primary bg-surface-2'
                  : 'border-transparent text-ink-secondary hover:text-ink-primary hover:bg-surface-2'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
