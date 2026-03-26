import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

const PRESETS = [
  { label: '>20% China', params: { dimension: 'geography', threshold: 20, operator: '>', category: 'China' } },
  { label: '>30% Fixed Income', params: { dimension: 'asset_class', threshold: 30, operator: '>', category: 'Fixed Income' } },
  { label: '>20% Info Tech', params: { dimension: 'sector', threshold: 20, operator: '>', category: 'Information Technology' } },
  { label: '>10% Alternatives', params: { dimension: 'asset_class', threshold: 10, operator: '>', category: 'Alternatives' } },
  { label: '>50% Equities', params: { dimension: 'asset_class', threshold: 50, operator: '>', category: 'Equities' } },
  { label: '>5% India', params: { dimension: 'geography', threshold: 5, operator: '>', category: 'India' } },
]

const BAR_COLORS = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

export default function CrossPortfolioSearch() {
  const [form, setForm] = useState({ dimension: 'geography', threshold: '20', operator: '>', category: '' })
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const applyPreset = (params) => {
    setForm({ ...params, threshold: String(params.threshold) })
    setResults(null)
  }

  const run = async () => {
    setLoading(true); setErr(null); setResults(null)
    try {
      const res = await fetch(`${API_BASE}/api/analysis/cross-portfolio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dimension: form.dimension,
          threshold: parseFloat(form.threshold),
          operator: form.operator,
          category: form.category.trim() || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'API error')
      setResults(data)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  const queryString = results
    ? `${results.query.dimension} ${results.query.operator} ${results.query.threshold}%${results.query.category ? ` (${results.query.category})` : ''}`
    : ''

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Cross-Portfolio Screening</h2>
        <p className="text-sm text-gray-500 mt-1">Deterministic exposure queries across all processed clients — no AI.</p>
      </div>

      {/* Query builder */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Query Builder</h3>
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Dimension</label>
            <select value={form.dimension} onChange={e => set('dimension', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="geography">Geography</option>
              <option value="asset_class">Asset Class</option>
              <option value="sector">Sector</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Operator</label>
            <select value={form.operator} onChange={e => set('operator', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {['>', '>=', '<', '<=', '=='].map(op => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Threshold (%)</label>
            <input type="number" value={form.threshold} onChange={e => set('threshold', e.target.value)}
              min="0" max="100" step="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Category <span className="text-gray-400">(optional)</span></label>
            <input type="text" value={form.category} onChange={e => set('category', e.target.value)}
              placeholder="e.g. China, Equities"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={run} disabled={loading}
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors">
            {loading ? 'Querying…' : 'Run Query'}
          </button>
          {PRESETS.map(p => (
            <button key={p.label} onClick={() => applyPreset(p.params)}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-indigo-50 hover:text-indigo-700 transition-colors">
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{err}</div>}

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-10 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      )}

      {results && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              {results.count === 0 ? 'No matches' : `${results.count} client${results.count !== 1 ? 's' : ''} matched`}
            </h3>
            <code className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded">
              {queryString}
            </code>
          </div>

          {results.count === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <p className="text-3xl mb-3">🔍</p>
              <p className="text-sm">No clients matched this query.</p>
              <p className="text-xs mt-1 text-gray-300">Try a lower threshold or different category.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.results.map((r, i) => {
                const maxPct = Math.max(...r.matches.map(m => m.percentage))
                return (
                  <div key={i} className="border border-gray-100 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="font-semibold text-gray-900">
                          {r.client_id.replace('_Client', '').replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs text-gray-400">${(r.total_value / 1e6).toFixed(2)}M AUM</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-black text-indigo-600">{maxPct.toFixed(1)}%</p>
                        <p className="text-xs text-gray-400">highest match</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {r.matches.map((m, j) => (
                        <div key={j}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-600 font-medium">{m.category}</span>
                            <span className="text-gray-900 font-semibold">{m.percentage.toFixed(1)}%</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${Math.min(m.percentage, 100)}%`, backgroundColor: BAR_COLORS[j % BAR_COLORS.length] }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
