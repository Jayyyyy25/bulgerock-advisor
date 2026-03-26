import { useState, useEffect, useRef } from 'react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import AllocationCharts from './components/AllocationCharts'
import StressTestWidget from './components/StressTestWidget'
import CrossPortfolioSearch from './components/CrossPortfolioSearch'

const API_BASE = 'http://localhost:8000'

function formatName(clientId) {
  return (clientId || '').replace('_Client', '').replace(/_/g, ' ')
}

export default function App() {
  const [clients, setClients] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [clientData, setClientData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loadingClients, setLoadingClients] = useState(true)
  const [loadingClient, setLoadingClient] = useState(false)
  const [error, setError] = useState(null)

  // Load client list on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/analysis/portfolios`)
      .then(r => r.json())
      .then(d => {
        setClients(d.portfolios || [])
        if (d.portfolios?.length > 0) selectClient(d.portfolios[0].client_id)
      })
      .catch(() => setError('Cannot reach API. Run: uvicorn api.main:app --reload --port 8000'))
      .finally(() => setLoadingClients(false))
  }, [])

  const selectClient = (id) => {
    setSelectedId(id)
    setClientData(null)
    setLoadingClient(true)
    setActiveTab('overview')
    fetch(`${API_BASE}/api/analysis/portfolios/${id}`)
      .then(r => r.json())
      .then(d => setClientData(d))
      .catch(() => setError('Failed to load client data.'))
      .finally(() => setLoadingClient(false))
  }

  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [uploadSuccess, setUploadSuccess] = useState(null)
  const [portfolioName, setPortfolioName] = useState('')
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0])
  const fileInputRef = useRef(null)

  const refreshClients = () =>
    fetch(`${API_BASE}/api/analysis/portfolios`)
      .then(r => r.json())
      .then(d => setClients(d.portfolios || []))

  const handleUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Please select a PDF file.')
      return
    }
    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    const form = new FormData()
    form.append('file', file)
    if (portfolioName.trim()) form.append('portfolio_name', portfolioName.trim())
    form.append('as_of_date', asOfDate)

    try {
      const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) {
        const detail = data.detail
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Upload failed')
      }

      await refreshClients()
      selectClient(data.client_id)
      setUploadSuccess(data.skipped ? 'Already processed — loaded existing.' : `${data.holdings_extracted} holdings stored.`)
      setTimeout(() => setUploadSuccess(null), 4000)
    } catch (e) {
      console.error('Upload error:', e)
      setUploadError(e.message || 'Network error — is the backend running on port 8000?')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const chartRef = useRef(null)
  const [exportingPDF, setExportingPDF] = useState(false)

  const exportToPDF = async () => {
    if (!chartRef.current || !clientData) return
    setExportingPDF(true)
    try {
      const el = chartRef.current

      // Force a wider render so Recharts has room and cards don't overflow
      const prevMinWidth = el.style.minWidth
      el.style.minWidth = '1500px'
      // Wait for Recharts ResizeObserver to re-layout at the new width
      await new Promise(r => setTimeout(r, 500))

      const canvas = await html2canvas(el, {
        scale: 1.5,
        useCORS: true,
        backgroundColor: '#f8fafc',
        scrollX: 0,
        scrollY: 0,
      })

      el.style.minWidth = prevMinWidth
      const img = canvas.toDataURL('image/png')
      const pdf = new jsPDF('l', 'mm', 'a4')  // landscape A4
      const pageW = pdf.internal.pageSize.getWidth()
      const pageH = pdf.internal.pageSize.getHeight()

      // Header
      const title = `${formatName(selectedId)} — Portfolio Summary`
      const subtitle = `Generated ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}  |  SAMPLE / ANONYMISED DATA`
      pdf.setFont('helvetica', 'bold')
      pdf.setFontSize(13)
      pdf.setTextColor(15, 23, 42)
      pdf.text(title, pageW / 2, 9, { align: 'center' })
      pdf.setFont('helvetica', 'normal')
      pdf.setFontSize(8)
      pdf.setTextColor(100, 116, 139)
      pdf.text(subtitle, pageW / 2, 14, { align: 'center' })
      pdf.setDrawColor(226, 232, 240)
      pdf.line(10, 17, pageW - 10, 17)

      // Image below header
      const headerBottom = 20
      const availH = pageH - headerBottom
      const ratio = canvas.width / canvas.height
      const imgH = pageW / ratio
      if (imgH <= availH) {
        pdf.addImage(img, 'PNG', 0, headerBottom, pageW, imgH)
      } else {
        const imgW = availH * ratio
        pdf.addImage(img, 'PNG', (pageW - imgW) / 2, headerBottom, imgW, availH)
      }

      pdf.save(`${selectedId}_portfolio_summary.pdf`)
    } finally {
      setExportingPDF(false)
    }
  }

  const tabs = ['overview', 'stress-test']
  const tabLabels = { 'overview': 'Overview', 'stress-test': 'Stress Test' }

  return (
    <div className="h-screen bg-gray-50 flex font-sans overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col flex-shrink-0 h-screen sticky top-0">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-indigo-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">B</div>
            <div>
              <p className="font-bold text-white leading-none">BugleRock</p>
              <p className="text-xs text-slate-400 mt-0.5">Portfolio Analyzer</p>
            </div>
          </div>
        </div>

        {/* Client list — scrollable, constrained by flex */}
        <div className="flex-1 overflow-y-auto min-h-0 px-3 py-4 scrollbar-hide">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">Clients</p>
          {loadingClients && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-400"></div>
            </div>
          )}
          {clients.map(c => (
            <button
              key={c.client_id}
              onClick={() => { setActiveTab('overview'); selectClient(c.client_id) }}
              className={`w-full text-left px-3 py-3 rounded-lg mb-1 transition-colors ${
                selectedId === c.client_id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <div className="text-sm font-medium truncate">{formatName(c.client_id)}</div>
              <div className="text-xs mt-0.5 opacity-60">
                ${(c.total_value / 1e6).toFixed(2)}M AUM
              </div>
            </button>
          ))}
        </div>

        {/* Upload PDF */}
        <div className="px-3 py-4 border-t border-slate-800 space-y-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => handleUpload(e.target.files?.[0])}
          />
          <input
            type="text"
            value={portfolioName}
            onChange={e => setPortfolioName(e.target.value)}
            placeholder="Portfolio name (optional — auto-detected)"
            className="w-full px-2 py-1.5 rounded-md bg-slate-800 text-slate-200 text-xs placeholder-slate-500 border border-slate-700 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="date"
            value={asOfDate}
            onChange={e => setAsOfDate(e.target.value)}
            className="w-full px-2 py-1.5 rounded-md bg-slate-800 text-slate-200 text-xs border border-slate-700 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={() => !uploading && fileInputRef.current?.click()}
            disabled={uploading}
            className={`w-full px-3 py-3 rounded-lg border-2 border-dashed transition-colors text-center ${
              uploading
                ? 'border-slate-700 text-slate-500 cursor-not-allowed'
                : 'border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-indigo-400'
            }`}
          >
            {uploading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-400" />
                <span className="text-xs">Processing PDF…</span>
              </div>
            ) : (
              <div>
                <div className="text-lg mb-0.5">＋</div>
                <div className="text-xs font-medium">Upload PDF</div>
              </div>
            )}
          </button>
          {uploadSuccess && (
            <p className="text-xs text-green-400 text-center mt-2">{uploadSuccess}</p>
          )}
          {uploadError && (
            <p className="text-xs text-red-400 text-center mt-2">{uploadError}</p>
          )}
        </div>

        {/* Cross-portfolio button */}
        <div className="px-3 pb-4 border-t border-slate-800 pt-0">
          <button
            onClick={() => setActiveTab('cross-portfolio')}
            className={`w-full text-left px-3 py-3 rounded-lg transition-colors ${
              activeTab === 'cross-portfolio'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <div className="text-sm font-medium">Cross-Portfolio</div>
            <div className="text-xs mt-0.5 opacity-60">Screen all clients</div>
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">

        {/* Header */}
        {activeTab !== 'cross-portfolio' && (
          <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between">
            <div>
              {selectedId ? (
                <>
                  <h1 className="text-lg font-semibold text-gray-900">{formatName(selectedId)}</h1>
                  {clientData && (
                    <p className="text-sm text-gray-500">
                      Total Value:{' '}
                      <span className="font-semibold text-gray-700">
                        ${clientData.total_value?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </p>
                  )}
                </>
              ) : (
                <h1 className="text-lg font-semibold text-gray-900">Select a client</h1>
              )}
            </div>

            {selectedId && (
              <div className="flex items-center gap-3">
                {activeTab === 'overview' && clientData && (
                  <button
                    onClick={exportToPDF}
                    disabled={exportingPDF}
                    className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {exportingPDF ? (
                      <><div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white" /> Exporting…</>
                    ) : (
                      <> ↓ Download PDF</>
                    )}
                  </button>
                )}
                <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
                  {tabs.map(t => (
                    <button
                      key={t}
                      onClick={() => setActiveTab(t)}
                      className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        activeTab === t
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {tabLabels[t]}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </header>
        )}

        {/* Content */}
        <main className="flex-1 overflow-auto p-8">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {activeTab === 'cross-portfolio' && (
            <CrossPortfolioSearch />
          )}

          {activeTab !== 'cross-portfolio' && loadingClient && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
            </div>
          )}

          {activeTab === 'overview' && clientData && !loadingClient && (
            <AllocationCharts ref={chartRef} data={clientData} />
          )}

          {activeTab === 'stress-test' && selectedId && !loadingClient && (
            <StressTestWidget clientId={selectedId} />
          )}
        </main>
      </div>
    </div>
  )
}
