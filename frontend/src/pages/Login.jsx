import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('dealer1@example.com')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-ink-primary font-semibold text-lg tracking-wide">PETRO OPS</div>
          <div className="text-ink-muted text-sm mt-1">Dealer decision intelligence platform</div>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-ink-secondary text-xs mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-ink-primary text-sm focus:outline-none focus:border-amber"
              required
            />
          </div>
          <div>
            <label className="block text-ink-secondary text-xs mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface-2 border border-line rounded px-3 py-2 text-ink-primary text-sm focus:outline-none focus:border-amber"
              required
            />
          </div>
          {error && <div className="text-bad text-sm">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amber text-canvas font-medium rounded py-2 text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="text-ink-muted text-xs text-center pt-1">
            Demo login: dealer1@example.com / password123
          </p>
        </form>
      </div>
    </div>
  )
}
