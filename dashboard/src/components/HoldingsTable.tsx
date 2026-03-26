import type { HoldingItem } from "../types";

interface Props {
  holdings: HoldingItem[];
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

export function HoldingsTable({ holdings }: Props) {
  if (!holdings.length) return <p className="text-gray-400 text-sm">No holdings data.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 font-semibold text-gray-600">Ticker</th>
            <th className="text-left py-2 font-semibold text-gray-600">Name</th>
            <th className="text-left py-2 font-semibold text-gray-600">Class</th>
            <th className="text-left py-2 font-semibold text-gray-600">Sector</th>
            <th className="text-right py-2 font-semibold text-gray-600">Market Value</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 font-mono font-medium text-blue-700">{h.ticker}</td>
              <td className="py-2 text-gray-700">{h.security_name ?? "—"}</td>
              <td className="py-2">
                <span className="px-2 py-0.5 rounded-full text-xs bg-blue-50 text-blue-700">
                  {h.asset_class ?? "—"}
                </span>
              </td>
              <td className="py-2 text-gray-500 text-xs">{h.sector ?? "—"}</td>
              <td className="py-2 text-right font-medium">{fmt(h.market_value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
