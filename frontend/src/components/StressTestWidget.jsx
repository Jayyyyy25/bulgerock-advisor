import { useState, useRef } from 'react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

const API_BASE = 'http://localhost:8000'

const PRESETS = [
  'US Fed rate hike 25bp',
  'China tech crackdown regulation',
  'Singapore REIT sector selloff',
  'Global recession fears emerge',
  'Oil price spike +30%',
]

const SEVERITY = {
  Critical: { ring: 'border-red-400',   badge: 'bg-red-100 text-red-700',     dot: 'bg-red-500'    },
  High:     { ring: 'border-orange-400', badge: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500' },
  Moderate: { ring: 'border-yellow-400', badge: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  Low:      { ring: 'border-blue-400',   badge: 'bg-blue-100 text-blue-700',   dot: 'bg-blue-500'   },
  Minimal:  { ring: 'border-green-400',  badge: 'bg-green-100 text-green-700', dot: 'bg-green-500'  },
}

function formatName(clientId) {
  return (clientId || '').replace('_Client', '').replace(/_/g, ' ')
}

function formatCcy(val) {
  const abs = Math.abs(val)
  const sign = val < 0 ? '-' : ''
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  return `${sign}$${(abs / 1e3).toFixed(0)}K`
}

function ImpactGauge({ score }) {
  const pct = Math.round(((score + 10) / 20) * 100)
  const color = score <= -5 ? '#ef4444' : score < 0 ? '#f59e0b' : score === 0 ? '#6b7280' : score < 5 ? '#10b981' : '#059669'
  const label = score <= -5 ? 'Severe' : score < 0 ? 'Negative' : score === 0 ? 'Neutral' : score < 5 ? 'Positive' : 'Very Positive'

  return (
    <div className="flex flex-col items-center gap-2 min-w-[140px]">
      <div className="text-5xl font-black" style={{ color }}>
        {score > 0 ? `+${score}` : score}
      </div>
      <div className="text-xs text-gray-500">Impact Score</div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <div className="text-xs font-medium" style={{ color }}>{label}</div>
    </div>
  )
}

function AssetImpactTable({ impacts, totalLossPct }) {
  if (!impacts?.length) return null
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Asset Class Impact</h4>
        {totalLossPct != null && (
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
            totalLossPct < 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
          }`}>
            Est. portfolio {totalLossPct < 0 ? 'loss' : 'gain'}: {Math.abs(totalLossPct).toFixed(1)}%
          </span>
        )}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="text-left text-xs text-gray-400 font-medium pb-2">Asset Class</th>
            <th className="text-right text-xs text-gray-400 font-medium pb-2">Current Value</th>
            <th className="text-right text-xs text-gray-400 font-medium pb-2">Est. Change</th>
            <th className="text-right text-xs text-gray-400 font-medium pb-2">$ Impact</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {impacts.map((row, i) => (
            <tr key={i}>
              <td className="py-2.5 font-medium text-gray-800">{row.asset_class}</td>
              <td className="py-2.5 text-right text-gray-600">{formatCcy(row.current_value)}</td>
              <td className={`py-2.5 text-right font-semibold ${row.estimated_change_pct < 0 ? 'text-red-600' : 'text-green-600'}`}>
                {row.estimated_change_pct > 0 ? '+' : ''}{row.estimated_change_pct.toFixed(1)}%
              </td>
              <td className={`py-2.5 text-right font-semibold ${row.estimated_change_value < 0 ? 'text-red-600' : 'text-green-600'}`}>
                {row.estimated_change_value > 0 ? '+' : ''}{formatCcy(row.estimated_change_value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RebalancingActions({ actions }) {
  if (!actions?.length) return null
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Recommended Rebalancing</h4>
      <div className="space-y-2">
        {actions.map((a, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
            <span className={`flex-shrink-0 text-xs font-bold px-2 py-0.5 rounded mt-0.5 ${
              a.action === 'REDUCE' ? 'bg-red-100 text-red-700' :
              a.action === 'BUY'    ? 'bg-green-100 text-green-700' :
                                      'bg-gray-200 text-gray-600'
            }`}>{a.action}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-gray-800">{a.asset_class}</span>
                <span className="text-sm font-bold text-gray-900">{formatCcy(a.trade_value)}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                <span className="text-xs text-gray-500">{a.from_pct?.toFixed(1)}%</span>
                <span className="text-xs text-gray-400">→</span>
                <span className="text-xs font-medium text-gray-700">{a.to_pct?.toFixed(1)}%</span>
                {a.rationale && <span className="text-xs text-gray-400">· {a.rationale}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function StressTestWidget({ clientId }) {
  const [event, setEvent]     = useState('')
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr]         = useState(null)
  const [exporting, setExporting] = useState(false)
  const exportRef = useRef(null)

  const run = async () => {
    if (!event.trim()) return
    setLoading(true); setErr(null); setResult(null)
    try {
      const res = await fetch(`${API_BASE}/api/analysis/stress-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId, market_event: event }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'API error')
      setResult(data.analysis)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  const exportPDF = async () => {
    if (!exportRef.current || !result) return
    setExporting(true)
    try {
      const el = exportRef.current
      const prevMinWidth = el.style.minWidth
      el.style.minWidth = '900px'
      await new Promise(r => setTimeout(r, 400))

      const canvas = await html2canvas(el, {
        scale: 1.5,
        useCORS: true,
        backgroundColor: '#f8fafc',
        scrollX: 0,
        scrollY: 0,
      })
      el.style.minWidth = prevMinWidth

      const img = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const pageW = pdf.internal.pageSize.getWidth()
      const pageH = pdf.internal.pageSize.getHeight()

      // Header
      pdf.setFont('helvetica', 'bold')
      pdf.setFontSize(13)
      pdf.setTextColor(15, 23, 42)
      pdf.text(`Portfolio Impact Summary — ${formatName(clientId)}`, pageW / 2, 9, { align: 'center' })
      pdf.setFont('helvetica', 'normal')
      pdf.setFontSize(7.5)
      pdf.setTextColor(100, 116, 139)
      pdf.text(
        `Market Event: ${event}  |  ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}  |  AI-ESTIMATED IMPACT`,
        pageW / 2, 14, { align: 'center' }
      )
      pdf.setDrawColor(226, 232, 240)
      pdf.line(10, 17, pageW - 10, 17)

      // Content image
      const headerBottom = 20
      const availH = pageH - headerBottom
      const ratio = canvas.width / canvas.height
      const imgH = pageW / ratio
      if (imgH <= availH) {
        pdf.addImage(img, 'PNG', 0, headerBottom, pageW, imgH)
      } else {
        const scale = availH / imgH
        pdf.addImage(img, 'PNG', (pageW - pageW * scale) / 2, headerBottom, pageW * scale, availH)
      }

      pdf.save(`${clientId}_impact_${event.replace(/\s+/g, '_').slice(0, 30)}.pdf`)
    } finally {
      setExporting(false)
    }
  }

  const sev = result ? (SEVERITY[result.impact_severity] ?? SEVERITY.Moderate) : null

  return (
    <div className="max-w-4xl space-y-5">

      {/* Input card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Market Event Scenario</h3>
        <div className="flex gap-3">
          <input
            value={event}
            onChange={e => setEvent(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="e.g. US Fed rate hike 25bp, China tech crackdown..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <button
            onClick={run}
            disabled={loading || !event.trim()}
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Analysing…' : 'Run Analysis'}
          </button>
        </div>

        {/* Preset pills */}
        <div className="flex flex-wrap gap-2 mt-3">
          {PRESETS.map(p => (
            <button key={p} onClick={() => setEvent(p)}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-indigo-50 hover:text-indigo-700 transition-colors">
              {p}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{err}</div>}

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
          <p className="text-sm text-gray-500">Claude is analysing portfolio impact…</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Download button */}
          <div className="flex justify-end">
            <button
              onClick={exportPDF}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {exporting
                ? <><div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white" /> Exporting…</>
                : <>↓ Download PDF Summary</>
              }
            </button>
          </div>

          <div ref={exportRef} className="space-y-4 bg-gray-50 rounded-xl p-1">

            {/* Score + summary */}
            <div className={`bg-white rounded-xl border-2 shadow-sm p-6 flex items-start gap-8 ${sev.ring}`}>
              <ImpactGauge score={result.portfolio_impact_score} />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-3">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${sev.badge}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${sev.dot}`} />
                    {result.impact_severity} Impact
                  </span>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">{result.executive_summary}</p>
              </div>
            </div>

            {/* Asset class impact table */}
            <AssetImpactTable
              impacts={result.asset_class_impacts}
              totalLossPct={result.estimated_portfolio_loss_pct}
            />

            {/* Rebalancing actions */}
            <RebalancingActions actions={result.rebalancing_actions} />

            {/* Vulnerable / Resilient */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-red-100 shadow-sm p-6">
                <h4 className="text-xs font-semibold text-red-500 uppercase tracking-wider mb-4">⚠ Vulnerable Holdings</h4>
                <div className="divide-y divide-gray-50">
                  {result.vulnerable_holdings?.map((h, i) => (
                    <div key={i} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-800">{h.security_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          h.estimated_impact === 'High' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>{h.estimated_impact}</span>
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed">{h.reason}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-green-100 shadow-sm p-6">
                <h4 className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-4">✓ Resilient Holdings</h4>
                <div className="divide-y divide-gray-50">
                  {result.resilient_holdings?.map((h, i) => (
                    <div key={i} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-800">{h.security_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          h.estimated_impact === 'Positive' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                        }`}>{h.estimated_impact}</span>
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed">{h.reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-400 text-center pb-1">
              AI-estimated impact only — not financial advice. Dollar figures derived from AI scenario estimates applied to actual portfolio values.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
