import React, { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { forecastApi } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Forecast() {
  const { user } = useAuth()
  const [fuelType, setFuelType] = useState('DIESEL')
  const [forecast, setForecast] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    setError('')
    forecastApi
      .get(user.dealerId, fuelType, 14)
      .then((res) => setForecast(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load forecast'))
  }, [user, fuelType])

  const chartData = forecast?.points.map((p) => ({ date: p.date.slice(5), qty: p.predicted_qty_l })) || []

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['PETROL', 'DIESEL'].map((ft) => (
          <button
            key={ft}
            onClick={() => setFuelType(ft)}
            className={`px-3 py-1.5 text-sm rounded border ${
              fuelType === ft
                ? 'bg-amber text-canvas border-amber font-medium'
                : 'border-line text-ink-secondary hover:text-ink-primary'
            }`}
          >
            {ft}
          </button>
        ))}
      </div>

      {error && <div className="text-bad text-sm">{error}</div>}

      {forecast && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="card p-4">
              <div className="text-ink-muted text-xs uppercase">Model</div>
              <div className="data-num text-ink-primary mt-1">{forecast.model_version}</div>
            </div>
            <div className="card p-4">
              <div className="text-ink-muted text-xs uppercase">Confidence</div>
              <div className="data-num text-ink-primary mt-1">{(forecast.confidence * 100).toFixed(0)}%</div>
            </div>
            <div className="card p-4">
              <div className="text-ink-muted text-xs uppercase">MAPE (backtest)</div>
              <div className="data-num text-ink-primary mt-1">{forecast.mape?.toFixed(2)}%</div>
            </div>
          </div>

          <div className="card p-5">
            <div className="text-ink-secondary text-xs uppercase tracking-wide mb-4">
              {fuelType} demand forecast — next {forecast.horizon_days} days
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A333A" />
                <XAxis dataKey="date" stroke="#9AA7AE" fontSize={12} />
                <YAxis stroke="#9AA7AE" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1D242A', border: '1px solid #2A333A', borderRadius: 8 }}
                  labelStyle={{ color: '#E7ECEE' }}
                />
                <Line type="monotone" dataKey="qty" stroke="#E8A23A" strokeWidth={2} dot={{ r: 3 }} name="Predicted L" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
