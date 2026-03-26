import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useClientList } from "../hooks/useClientData";
import type { Client } from "../types";

const fmt = (n?: number) =>
  n !== undefined
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(n)
    : "—";

const RISK_COLORS: Record<string, string> = {
  aggressive: "bg-red-100 text-red-700",
  moderate: "bg-yellow-100 text-yellow-700",
  conservative: "bg-green-100 text-green-700",
};

export function ClientSearch() {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const navigate = useNavigate();

  const { data: clients = [], isLoading } = useClientList({
    name: search || undefined,
    risk_profile: riskFilter || undefined,
  });

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Pocket IA — Client Book</h1>

      <div className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Risk Profiles</option>
          <option value="conservative">Conservative</option>
          <option value="moderate">Moderate</option>
          <option value="aggressive">Aggressive</option>
        </select>
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading clients...</p>}

      <div className="space-y-2">
        {clients.map((c: Client) => (
          <button
            key={c.client_id}
            onClick={() => navigate(`/client/${c.client_id}`)}
            className="w-full text-left bg-white rounded-xl shadow-sm border border-gray-100 px-5 py-4 hover:shadow-md hover:border-blue-200 transition-all"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900">{c.full_name}</p>
                <p className="text-sm text-gray-400">{c.email} · {c.client_id}</p>
              </div>
              <div className="text-right space-y-1">
                <p className="font-bold text-gray-800">{fmt(c.aum)}</p>
                {c.risk_profile && (
                  <span className={`px-2 py-0.5 rounded-full text-xs capitalize ${RISK_COLORS[c.risk_profile] ?? "bg-gray-100 text-gray-600"}`}>
                    {c.risk_profile}
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
