import { useParams, useNavigate } from "react-router-dom";
import { useClientData } from "../hooks/useClientData";
import { AllocationDonut } from "./AllocationDonut";
import { HoldingsTable } from "./HoldingsTable";
import { PolicyCard } from "./PolicyCard";

const fmt = (n?: number) =>
  n !== undefined
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
    : "—";

const RISK_COLORS: Record<string, string> = {
  aggressive: "bg-red-100 text-red-700 border-red-200",
  moderate: "bg-yellow-100 text-yellow-700 border-yellow-200",
  conservative: "bg-green-100 text-green-700 border-green-200",
};

export function Client360() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const { client, portfolio, policies, isLoading, isError } = useClientData(clientId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (isError || !client) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <p className="text-red-500">Failed to load client data. Check the API connection.</p>
        <button onClick={() => navigate("/")} className="mt-4 text-blue-600 underline text-sm">
          ← Back to clients
        </button>
      </div>
    );
  }

  const urgentPolicies = policies.filter((p) => (p.days_until_renewal ?? 99) <= 30);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => navigate("/")} className="text-blue-600 text-sm hover:underline mb-2 block">
            ← Back to clients
          </button>
          <h1 className="text-3xl font-bold text-gray-900">{client.full_name}</h1>
          <p className="text-gray-500 mt-1">{client.email} · {client.phone}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-900">{fmt(client.aum)}</p>
          <p className="text-xs text-gray-400 mb-1">Total AUM</p>
          {client.risk_profile && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize border ${RISK_COLORS[client.risk_profile] ?? ""}`}>
              {client.risk_profile}
            </span>
          )}
        </div>
      </div>

      {/* Urgent policy banner */}
      {urgentPolicies.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <span className="text-red-500 text-xl">⚠️</span>
          <p className="text-red-700 text-sm font-medium">
            {urgentPolicies.length} policy renewal{urgentPolicies.length > 1 ? "s" : ""} due within 30 days.
          </p>
        </div>
      )}

      {/* Portfolio data as of date */}
      {portfolio?.as_of_date && (
        <p className="text-xs text-gray-400">Portfolio data as of {portfolio.as_of_date}</p>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Asset Allocation</h2>
          <AllocationDonut data={portfolio?.allocation ?? []} />
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Top 5 Holdings</h2>
          <HoldingsTable holdings={portfolio?.top_holdings ?? []} />
        </div>
      </div>

      {/* Policies */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
        <h2 className="font-semibold text-gray-700 mb-4">
          Insurance Policies
          {policies.length > 0 && (
            <span className="ml-2 text-xs text-gray-400 font-normal">(next 90 days)</span>
          )}
        </h2>
        {policies.length === 0 ? (
          <p className="text-gray-400 text-sm">No upcoming renewals in the next 90 days.</p>
        ) : (
          policies.map((p) => <PolicyCard key={p.policy_id} policy={p} />)
        )}
      </div>
    </div>
  );
}
