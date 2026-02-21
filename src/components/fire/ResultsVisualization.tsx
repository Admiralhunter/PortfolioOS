/**
 * FIRE simulation results visualization — probability fan chart,
 * success rate gauge, and summary statistics.
 *
 * Fan chart displays 5th/25th/50th/75th/95th percentile portfolio paths.
 * Success rate shows probability of portfolio surviving the full horizon.
 * References: Bengen (1994), Trinity Study (1998).
 */

import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from "recharts";
import type { SimulationResult } from "../../types";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function SuccessGauge({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference * (1 - rate);
  const color =
    pct >= 90
      ? "var(--color-success)"
      : pct >= 70
        ? "var(--color-warning)"
        : "var(--color-destructive)";

  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 50 50)"
        />
        <text
          x="50"
          y="46"
          textAnchor="middle"
          className="text-2xl font-bold"
          fill="var(--color-foreground)"
          fontSize="22"
        >
          {pct}%
        </text>
        <text
          x="50"
          y="62"
          textAnchor="middle"
          fill="var(--color-muted-foreground)"
          fontSize="9"
        >
          success rate
        </text>
      </svg>
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="p-3 bg-muted rounded-md">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium text-foreground">{value}</p>
      {hint && <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>}
    </div>
  );
}

interface FanChartDatum {
  year: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
}

function buildFanChartData(
  percentiles: Record<number, number[]>
): FanChartDatum[] {
  const p5 = percentiles[5] ?? [];
  const p25 = percentiles[25] ?? [];
  const p50 = percentiles[50] ?? [];
  const p75 = percentiles[75] ?? [];
  const p95 = percentiles[95] ?? [];

  const len = Math.max(p5.length, p25.length, p50.length, p75.length, p95.length);
  const data: FanChartDatum[] = [];

  for (let i = 0; i < len; i++) {
    data.push({
      year: i,
      p5: p5[i] ?? 0,
      p25: p25[i] ?? 0,
      p50: p50[i] ?? 0,
      p75: p75[i] ?? 0,
      p95: p95[i] ?? 0,
    });
  }
  return data;
}

function FanChart({ data }: { data: FanChartDatum[] }) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="year"
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#262626"
            label={{
              value: "Year",
              position: "insideBottomRight",
              offset: -5,
              fill: "#a3a3a3",
              fontSize: 11,
            }}
          />
          <YAxis
            tickFormatter={formatCurrency}
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#262626"
            width={70}
          />
          <Tooltip
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                p5: "5th percentile",
                p25: "25th percentile",
                p50: "Median",
                p75: "75th percentile",
                p95: "95th percentile",
              };
              return [formatCurrency(Number(value ?? 0)), labels[String(name)] ?? String(name)];
            }}
            labelFormatter={(label) => `Year ${label}`}
            contentStyle={{
              backgroundColor: "#141414",
              border: "1px solid #262626",
              borderRadius: "6px",
              color: "#fafafa",
              fontSize: "12px",
            }}
          />

          {/* 5th-95th band (lightest) */}
          <Area
            type="monotone"
            dataKey="p95"
            stroke="none"
            fill="#3b82f6"
            fillOpacity={0.08}
            stackId="band-outer"
          />
          <Area
            type="monotone"
            dataKey="p5"
            stroke="none"
            fill="#0a0a0a"
            fillOpacity={1}
            stackId="band-outer"
          />

          {/* 25th-75th band (medium) */}
          <Area
            type="monotone"
            dataKey="p75"
            stroke="none"
            fill="#3b82f6"
            fillOpacity={0.15}
            stackId="band-inner"
          />
          <Area
            type="monotone"
            dataKey="p25"
            stroke="none"
            fill="#0a0a0a"
            fillOpacity={1}
            stackId="band-inner"
          />

          {/* Median line */}
          <Line
            type="monotone"
            dataKey="p50"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

const STRATEGY_LABELS: Record<string, string> = {
  constant_dollar: "Constant Dollar (4% Rule)",
  constant_percentage: "Constant Percentage",
  guyton_klinger: "Guyton-Klinger Guardrails",
};

export function ResultsVisualization({
  result,
  initialPortfolio,
}: {
  result: SimulationResult;
  initialPortfolio: number;
}) {
  const fanData = buildFanChartData(result.percentiles);
  const withdrawalRate =
    initialPortfolio > 0
      ? ((result.percentiles[50]?.[1] !== undefined
          ? initialPortfolio - (result.percentiles[50]?.[1] ?? 0)
          : 0) /
          initialPortfolio) *
        100
      : 0;

  return (
    <div className="space-y-6">
      {/* Top row: success gauge + stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-center">
          <SuccessGauge rate={result.success_rate} />
        </div>
        <div className="bg-card border border-border rounded-lg p-4 space-y-3 md:col-span-2">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Summary Statistics
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              label="Median Final Value"
              value={formatCurrency(result.median_final_value)}
            />
            <StatCard
              label="Strategy"
              value={STRATEGY_LABELS[result.strategy] ?? result.strategy}
            />
            <StatCard
              label="5th Percentile (Worst Case)"
              value={formatCurrency(
                result.percentiles[5]?.[result.percentiles[5].length - 1] ?? 0
              )}
              hint="1-in-20 bad outcome"
            />
            <StatCard
              label="95th Percentile (Best Case)"
              value={formatCurrency(
                result.percentiles[95]?.[result.percentiles[95].length - 1] ?? 0
              )}
              hint="1-in-20 good outcome"
            />
          </div>
          {withdrawalRate > 0 && (
            <p className="text-xs text-muted-foreground">
              Effective withdrawal rate: {withdrawalRate.toFixed(1)}%
            </p>
          )}
        </div>
      </div>

      {/* Fan chart */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h4 className="text-sm font-semibold text-foreground mb-3">
          Portfolio Value Projections
        </h4>
        <p className="text-xs text-muted-foreground mb-4">
          Probability fan chart showing 5th/25th/50th/75th/95th percentile
          portfolio paths across {fanData.length > 0 ? fanData.length - 1 : 0}{" "}
          years.
        </p>
        <FanChart data={fanData} />
        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-primary inline-block" /> Median
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-3 bg-primary/15 inline-block rounded-sm" />{" "}
            25th-75th
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-3 bg-primary/8 inline-block rounded-sm" />{" "}
            5th-95th
          </span>
        </div>
      </div>
    </div>
  );
}
