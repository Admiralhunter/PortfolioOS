/**
 * Asset allocation pie chart — shows distribution by symbol.
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { useHoldings } from "../../hooks/useHoldings";
import { usePortfolioStore } from "../../stores/portfolio";

const COLORS = [
  "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
  "#ef4444", "#ec4899", "#6366f1", "#14b8a6", "#f97316",
];

export function AllocationChart() {
  const { selectedAccountId } = usePortfolioStore();
  const { data: holdings } = useHoldings(selectedAccountId ?? undefined);

  if (!holdings || holdings.length === 0) {
    return null;
  }

  const data = holdings.map((h) => ({
    name: h.symbol,
    value: h.cost_basis,
  }));

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((_entry, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => {
              const num = Number(value);
              return `$${num.toLocaleString()} (${((num / total) * 100).toFixed(1)}%)`;
            }}
            contentStyle={{
              backgroundColor: "#141414",
              border: "1px solid #262626",
              borderRadius: "6px",
              color: "#fafafa",
              fontSize: "12px",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "12px", color: "#a3a3a3" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
