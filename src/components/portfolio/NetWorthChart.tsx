/**
 * Net worth tracker — historical line chart with growth metrics.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useSnapshots } from "../../hooks/useSnapshots";
import { usePortfolioStore } from "../../stores/portfolio";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function NetWorthChart() {
  const { selectedAccountId } = usePortfolioStore();
  const { data: snapshots, isLoading } = useSnapshots(selectedAccountId);

  if (!selectedAccountId) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        Select an account to view net worth history
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-4 text-muted-foreground text-sm">Loading snapshots...</div>;
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No snapshot history available. Import transactions and reconcile to generate snapshots.
      </div>
    );
  }

  const chartData = snapshots.map((s) => ({
    date: s.date,
    value: s.total_value,
    costBasis: s.total_cost_basis,
    gain: s.unrealized_gain,
  }));

  return (
    <div className="space-y-4">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fill: "#a3a3a3", fontSize: 11 }}
              stroke="#262626"
            />
            <YAxis
              tickFormatter={formatCurrency}
              tick={{ fill: "#a3a3a3", fontSize: 11 }}
              stroke="#262626"
              width={70}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              labelFormatter={(label) => new Date(String(label)).toLocaleDateString()}
              contentStyle={{
                backgroundColor: "#141414",
                border: "1px solid #262626",
                borderRadius: "6px",
                color: "#fafafa",
                fontSize: "12px",
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="Total Value"
            />
            <Line
              type="monotone"
              dataKey="costBasis"
              stroke="#6366f1"
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name="Cost Basis"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <GrowthMetrics snapshots={snapshots} />
    </div>
  );
}

function GrowthMetrics({ snapshots }: { snapshots: Array<{ total_value: number; date: string }> }) {
  if (snapshots.length < 2) return null;

  const first = snapshots[0];
  const last = snapshots[snapshots.length - 1];
  const totalReturn = ((last.total_value - first.total_value) / first.total_value) * 100;

  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="p-3 bg-muted rounded-md">
        <p className="text-xs text-muted-foreground">Start</p>
        <p className="text-sm font-medium text-foreground">{formatCurrency(first.total_value)}</p>
        <p className="text-xs text-muted-foreground">{formatDate(first.date)}</p>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <p className="text-xs text-muted-foreground">Current</p>
        <p className="text-sm font-medium text-foreground">{formatCurrency(last.total_value)}</p>
        <p className="text-xs text-muted-foreground">{formatDate(last.date)}</p>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <p className="text-xs text-muted-foreground">Total Return</p>
        <p className={`text-sm font-medium ${totalReturn >= 0 ? "text-success" : "text-destructive"}`}>
          {totalReturn >= 0 ? "+" : ""}{totalReturn.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}
