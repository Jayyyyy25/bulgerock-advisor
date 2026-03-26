import type { Policy } from "../types";

interface Props {
  policy: Policy;
}

const fmt = (n?: number) =>
  n !== undefined
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
    : "—";

function urgencyBadge(days?: number) {
  if (days === undefined) return null;
  if (days <= 7)
    return <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-semibold">{days}d — URGENT</span>;
  if (days <= 30)
    return <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">{days}d</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">{days}d</span>;
}

export function PolicyCard({ policy }: Props) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div>
        <p className="font-medium text-gray-800">{policy.policy_type}</p>
        <p className="text-sm text-gray-500">{policy.insurer} · Coverage: {fmt(policy.coverage_amount)}</p>
      </div>
      <div className="text-right space-y-1">
        <div>{urgencyBadge(policy.days_until_renewal)}</div>
        <p className="text-xs text-gray-400">Renews: {policy.renewal_date} · Premium: {fmt(policy.premium)}/yr</p>
      </div>
    </div>
  );
}
