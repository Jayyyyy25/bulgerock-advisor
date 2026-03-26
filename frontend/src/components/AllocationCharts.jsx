import { forwardRef } from 'react'
import {
  PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const PALETTE = [
  '#4f46e5', '#06b6d4', '#10b981', '#f59e0b',
  '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
]

const RADIAN = Math.PI / 180
function PieLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.05) return null
  const r = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
      fontSize={11} fontWeight="700">
      {(percent * 100).toFixed(0)}%
    </text>
  )
}

function Card({ title, children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm p-6 ${className}`}>
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-5">{title}</h3>
      {children}
    </div>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 py-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

const AllocationCharts = forwardRef(function AllocationCharts({ data }, ref) {
  const allocationData = Object.entries(data.asset_allocation || {})
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value: parseFloat(value) }))

  const sectorData = Object.entries(data.sector_concentration || {})
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value: parseFloat(value) }))

  const geoData = Object.entries(data.geographic_exposure || {})
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value: parseFloat(value) }))

  const risk = data.risk_metrics || {}
  const holdings = data.top_10_holdings || []
  const aum = data.total_value || 0

  return (
    <div ref={ref} className="space-y-6">

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total AUM" value={`$${(aum / 1e6).toFixed(2)}M`} />
        <StatCard label="Est. Volatility" value={`${risk.estimated_volatility_pct ?? '—'}%`} sub="Equity-weighted proxy" />
        <StatCard label="Est. Sharpe Ratio" value={risk.estimated_sharpe_ratio ?? '—'} sub="MVP proxy" />
        <StatCard label="Top Holdings" value={`${holdings.length}`} sub="Shown below" />
      </div>

      {/* Allocation + Geography */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="Asset Allocation">
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Pie
                data={allocationData}
                cx="50%" cy="46%"
                outerRadius={120}
                dataKey="value"
                labelLine={false}
                label={PieLabel}
              >
                {allocationData.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Geographic Exposure">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={geoData} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
              <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={55} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} cursor={{ fill: '#f1f5f9' }} />
              <Bar dataKey="value" fill="#4f46e5" radius={[0, 4, 4, 0]} barSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Sector + Holdings */}
      <div className="grid grid-cols-2 gap-6">
        <Card title="Sector Concentration">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={sectorData} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
              <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={130} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} cursor={{ fill: '#f1f5f9' }} />
              <Bar dataKey="value" fill="#06b6d4" radius={[0, 4, 4, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Top 10 Holdings">
          <div className="divide-y divide-gray-50">
            {holdings.slice(0, 10).map((h, i) => {
              const pct = aum > 0 ? ((h.market_value / aum) * 100).toFixed(1) : 0
              return (
                <div key={i} className="flex items-center justify-between py-2.5">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-300 w-4 flex-shrink-0">{i + 1}</span>
                    <span className="text-sm text-gray-700">{h.security_name}</span>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <div className="text-sm font-semibold text-gray-900">
                      ${h.market_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                    <div className="text-xs text-gray-400">{pct}%</div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 text-center">
        Sample / anonymised data — AI-assisted assessment only, not financial advice.
      </p>
    </div>
  )
})

export default AllocationCharts
