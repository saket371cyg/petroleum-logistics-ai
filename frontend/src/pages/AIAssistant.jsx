import React, { useState } from 'react'
import { aiApi, ordersApi } from '../services/api'
import LogisticsDecisionCard from '../components/LogisticsDecisionCard'

const SUGGESTIONS = [
  'Should I order petrol?',
  'Should I order diesel?',
  'Which fuel should I order right now?',
  'How much petrol should I order?',
  'When should I order petrol?',
  'Generate an order for petrol.',
  'Find a tanker and driver for this order.',
  'What happens if I wait two days?',
  'Show me alternatives.',
  'What should I do today?',
]

export default function AIAssistant() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [lastQuestion, setLastQuestion] = useState('')
  const [errorState, setErrorState] = useState(null)

  const handleGenerateOrder = async (decision) => {
    const fuel = decision?.fuel || decision?.decision?.fuel || decision?.selected_fuel
    const quantity =
      decision?.quantities?.recommended_quantity_l ||
      decision?.decision?.quantity_liters ||
      decision?.quantity_liters ||
      decision?.recommended_quantity_l

    if (!fuel || !quantity) return

    try {
      const res = await ordersApi.create(fuel, quantity)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: `ORDER CONFIRMED: Order #${res.data.id} created for ${Number(quantity).toLocaleString()} L of ${fuel}.\nStatus: ${res.data.status || 'PENDING_APPROVAL'}.\nStaged in database awaiting dealer approval.`,
          sources: ['fuel_orders', 'dispatch_plans'],
          decision: { ...decision, generated_order_id: res.data.id, status: 'PENDING_APPROVAL' },
        },
      ])
    } catch (error) {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: error.response?.data?.detail || 'Unable to generate the order right now.',
          sources: [],
        },
      ])
    }
  }

  const ask = async (q) => {
    const text = q || question
    if (!text.trim()) return
    setLastQuestion(text)
    setErrorState(null)
    setMessages((m) => [...m, { role: 'user', text }])
    setQuestion('')
    setBusy(true)

    try {
      const res = await aiApi.query(text)
      const decision = res.data.decision || null
      const answer = res.data.answer || 'No recommendation available.'
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: answer,
          sources: res.data.data_sources || res.data.sources || [],
          decision,
        },
      ])
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'The logistics decision engine could not reach the server.'
      setErrorState(detail)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: `DECISION COULD NOT BE COMPLETED: ${detail}`,
          isError: true,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Quick Suggestions Pills */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => ask(s)}
            className="text-xs border border-line rounded px-3 py-1.5 text-ink-secondary hover:text-ink-primary hover:border-line-strong transition-colors bg-surface-2"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Main Conversation & Decision Control Center Area */}
      <div className="card p-5 min-h-[480px] flex flex-col bg-surface border border-line">
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="rounded border border-line bg-surface-2/40 p-6 text-center text-ink-secondary">
              <div className="font-semibold text-ink-primary text-sm tracking-wide uppercase">
                Petroleum Dealer Logistics Decision Engine
              </div>
              <p className="mt-1 text-xs max-w-lg mx-auto text-ink-muted leading-relaxed">
                Investigating dealer storage tanks, calibrated consumption forecasts, lead-time buffers, tanker compatibility & compliance, driver certifications, and refinery loading slots.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <button
                  type="button"
                  onClick={() => ask('Which fuel should I order right now?')}
                  className="rounded bg-amber px-3.5 py-1.5 text-xs font-semibold text-canvas hover:opacity-90 transition-opacity"
                >
                  Which fuel should I order right now?
                </button>
                <button
                  type="button"
                  onClick={() => ask('What should I do today?')}
                  className="rounded border border-line bg-surface-2 px-3.5 py-1.5 text-xs font-medium text-ink-primary hover:border-line-strong transition-colors"
                >
                  What should I do today?
                </button>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[95%] sm:max-w-[90%] rounded p-3.5 text-xs sm:text-sm ${
                  m.role === 'user'
                    ? 'bg-amber text-canvas font-medium ml-8'
                    : m.isError
                    ? 'bg-bad/5 border border-bad/30 text-ink-primary mr-8 w-full'
                    : 'bg-surface-2 text-ink-primary border border-line mr-8 w-full'
                }`}
              >
                {/* Text answer with whitespace formatting */}
                <div className="whitespace-pre-wrap font-sans leading-relaxed">
                  {m.text}
                </div>

                {/* Rich Logistics Decision Card */}
                {m.decision && (
                  <LogisticsDecisionCard
                    decision={m.decision}
                    onAsk={ask}
                    onGenerateOrder={handleGenerateOrder}
                  />
                )}

                {/* Error Retry CTA */}
                {m.isError && lastQuestion && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() => ask(lastQuestion)}
                      className="rounded border border-bad/50 bg-bad/10 px-3 py-1 font-mono text-xs font-semibold text-bad hover:bg-bad/20"
                    >
                      RETRY DECISION
                    </button>
                  </div>
                )}

                {/* Telemetry / Data Sources Checked */}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-line/40 pt-2 text-[10px] text-ink-muted font-mono">
                    <span>Verified:</span>
                    {m.sources.map((s, idx) => (
                      <span key={idx} className="rounded bg-surface-3 px-1.5 py-0.5 text-ink-secondary border border-line/40">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading State matching Part P */}
          {busy && (
            <div className="flex justify-start">
              <div className="rounded border border-line bg-surface-2 p-3 text-xs w-full max-w-lg">
                <div className="font-semibold text-ink-primary flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-amber animate-pulse" />
                  <span className="font-mono tracking-wider">ANALYZING LOGISTICS</span>
                </div>
                <div className="mt-2.5 grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px] text-ink-secondary font-mono">
                  <span className="text-good">✓ Inventory</span>
                  <span className="text-good">✓ Forecast</span>
                  <span className="text-amber">● Fleet</span>
                  <span className="text-ink-muted">○ Drivers</span>
                  <span className="text-ink-muted">○ Slots</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            ask()
          }}
          className="flex gap-2 mt-4 pt-4 border-t border-line"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask: 'Which fuel should I order right now?', 'Should I order diesel?', 'What should I do today?'…"
            className="flex-1 bg-surface-2 border border-line rounded px-3.5 py-2.5 text-xs sm:text-sm text-ink-primary focus:outline-none focus:border-amber font-sans"
          />
          <button
            type="submit"
            disabled={busy}
            className="bg-amber text-canvas text-xs sm:text-sm font-semibold rounded px-5 py-2.5 hover:opacity-90 disabled:opacity-50 transition-opacity uppercase tracking-wider"
          >
            {busy ? 'Evaluating…' : 'Ask'}
          </button>
        </form>
      </div>
    </div>
  )
}
