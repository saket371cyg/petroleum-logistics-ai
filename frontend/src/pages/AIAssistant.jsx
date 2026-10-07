import React, { useState } from 'react'
import { aiApi } from '../services/api'

const SUGGESTIONS = [
  "What's our diesel stock situation?",
  'Any compliance alerts?',
  'Which tankers are at maintenance risk?',
  'Give me an operations summary',
]

export default function AIAssistant() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)

  const ask = async (q) => {
    const text = q || question
    if (!text.trim()) return
    setMessages((m) => [...m, { role: 'user', text }])
    setQuestion('')
    setBusy(true)
    try {
      const res = await aiApi.query(text)
      setMessages((m) => [...m, { role: 'assistant', text: res.data.answer, sources: res.data.data_sources }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: e.response?.data?.detail || 'Something went wrong.' }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => ask(s)}
            className="text-xs border border-line rounded-full px-3 py-1.5 text-ink-secondary hover:text-ink-primary hover:border-line-strong"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="card p-5 min-h-[360px] flex flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto">
          {messages.length === 0 && (
            <div className="text-ink-muted text-sm">
              Ask about fuel stock, tankers, drivers, compliance, maintenance, or overall operations.
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[75%] rounded px-3 py-2 text-sm ${
                  m.role === 'user' ? 'bg-amber text-canvas' : 'bg-surface-2 text-ink-primary'
                }`}
              >
                {m.text}
                {m.sources && m.sources.length > 0 && (
                  <div className="text-xs text-ink-muted mt-1">Source: {m.sources.join(', ')}</div>
                )}
              </div>
            </div>
          ))}
        </div>

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
            placeholder="Ask about your operations…"
            className="flex-1 bg-surface-2 border border-line rounded px-3 py-2 text-sm text-ink-primary focus:outline-none focus:border-amber"
          />
          <button
            type="submit"
            disabled={busy}
            className="bg-amber text-canvas text-sm font-medium rounded px-4 py-2 hover:opacity-90 disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  )
}
