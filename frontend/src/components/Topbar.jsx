import React from 'react'
import { useAuth } from '../context/AuthContext'

export default function Topbar({ title }) {
  const { user, logout } = useAuth()
  return (
    <header className="h-14 border-b border-line flex items-center justify-between px-6 bg-canvas sticky top-0 z-10">
      <h1 className="text-ink-primary text-base font-medium">{title}</h1>
      <div className="flex items-center gap-4">
        <span className="text-ink-secondary text-sm">{user?.email}</span>
        <button
          onClick={logout}
          className="text-sm text-ink-secondary hover:text-ink-primary border border-line hover:border-line-strong rounded px-3 py-1 transition-colors"
        >
          Log out
        </button>
      </div>
    </header>
  )
}
