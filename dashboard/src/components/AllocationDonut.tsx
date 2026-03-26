import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from "recharts";
import type { AllocationItem } from "../types";

const COLORS = ["#4F81BD", "#C0504D", "#9BBB59", "#8064A2", "#4BACC6", "#F79646"];

interface Props {
  data: AllocationItem[];
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

export function AllocationDonut({ data }: Props) {
  if (!data.length) return <p className="text-gray-400 text-sm">No allocation data.</p>;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          dataKey="pct"
          nameKey="asset_class"
          cx="50%"
          cy="50%"
          innerRadius={65}
          outerRadius={105}
          paddingAngle={2}
          label={({ asset_class, pct }) => `${asset_class}: ${pct}%`}
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string, props: any) => [
            `${value}% (${formatCurrency(props.payload.total_value)})`,
            props.payload.asset_class,
          ]}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
