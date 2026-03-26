import { useState, useRef, useEffect } from 'react'

const API_BASE = 'http://localhost:8000'

const EXAMPLE_PROMPTS = [
  'Which clients have >20% allocation to China?',
  'Show me clients with more than 30% in Fixed Income',
  'Which clients have significant Technology sector exposure?',
  'Find portfolios with >50% in Equities',
  'Which clients have India exposure above 5%?',
  'Show clients exposed to both US equities and bonds',
]

function formatName(clientId) {
  return (clientId || '').replace('_Client', '').replace(/_/g, ' ')
}

const BAR_COLORS = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function ResultCards({ results }) {
  if (!results?.results?.length) return null
  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        {results.matched_clients} client{results.matched_clients !== 1 ? 's' : ''} matched
      </p>
      {results.results.map((r, i) => (
        <div key={i} className="bg-white border border-gray-200 rounded-lg px-4 py-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">{formatName(r.client_id)}</p>
              <p className="text-xs text-gray-400">${(r.total_value / 1e6).toFixed(2)}M total AUM</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-black text-indigo-600">{r.exposure_pct.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">
                ${r.exposure_value >= 1e6
                  ? `${(r.exposure_value / 1e6).toFixed(2)}M`
                  : `${(r.exposure_value / 1e3).toFixed(0)}K`} exposure
              </p>
            </div>
          </div>
          {r.matched_categories ? (
            <div className="space-y-1.5">
              {r.matched_categories.map((cat, j) => (
                <div key={j}>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-gray-500 font-medium">{cat.category}</span>
                    <span className="text-gray-700 font-semibold">{cat.percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(cat.percentage, 100)}%`,
                        backgroundColor: BAR_COLORS[(i + j) % BAR_COLORS.length],
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-500 font-medium">Matched exposure</span>
                <span className="text-gray-700 font-semibold">{r.exposure_pct.toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(r.exposure_pct, 100)}%`,
                    backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
                  }}
                />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function CrossPortfolioSearch() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const userText = (text || input).trim()
    if (!userText || loading) return

    setMessages(prev => [...prev, { role: 'user', content: userText }])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const res = await fetch(`${API_BASE}/api/analysis/cross-portfolio-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, history }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'API error')
      setMessages(prev => [...prev, { role: 'assistant', content: data.response, results: data.results }])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="max-w-3xl flex flex-col" style={{ height: 'calc(100vh - 8rem)' }}>

      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Cross-Portfolio Analysis</h2>
        <p className="text-sm text-gray-500 mt-1">
          Ask in natural language — AI-assisted screening across all client portfolios
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 min-h-0">

        {/* Empty state */}
        {isEmpty && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-5 py-8">
            <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700">Screen all client portfolios</p>
              <p className="text-xs text-gray-400 mt-1">Ask about exposure by geography, asset class, or sector</p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {EXAMPLE_PROMPTS.map(p => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-xs font-bold mr-2 mt-0.5">
                B
              </div>
            )}
            <div className={msg.role === 'user' ? 'max-w-sm' : 'max-w-xl'}>
              <div className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-50 text-gray-800 border border-gray-200'
              }`}>
                {msg.content}
              </div>
              {msg.role === 'assistant' && <ResultCards results={msg.results} />}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="flex-shrink-0 w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-xs font-bold mr-2">
              B
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700">{error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="e.g. Which clients have >20% China exposure?"
          disabled={loading}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          onClick={() => sendMessage()}
          disabled={!input.trim() || loading}
          className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  )
}
