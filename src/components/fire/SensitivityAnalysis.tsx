/**
 * Sensitivity analysis — vary a single parameter and visualize
 * how it affects success rate and median final value.
 */

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { useSimulationStore } from "../../stores/simulation";
import { useRunSensitivity } from "../../hooks/useSimulation";
import type { SensitivityParam, SensitivityResult } from "../../types";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

const TOOLTIP_STYLE = {
  backgroundColor: "#141414", border: "1px solid #262626",
  borderRadius: "6px", color: "#fafafa", fontSize: "12px",
};
const TICK_STYLE = { fill: "#a3a3a3", fontSize: 11 };

const PARAM_OPTIONS: Record<SensitivityParam, {
  label: string; defaultValues: number[]; formatValue: (v: number) => string;
}> = {
  withdrawal_rate: {
    label: "Withdrawal Rate",
    defaultValues: [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06],
    formatValue: (v) => `${(v * 100).toFixed(1)}%`,
  },
  inflation_rate: {
    label: "Inflation Rate",
    defaultValues: [0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
    formatValue: (v) => `${(v * 100).toFixed(1)}%`,
  },
  n_years: {
    label: "Time Horizon",
    defaultValues: [10, 15, 20, 25, 30, 35, 40, 45, 50],
    formatValue: (v) => `${v}yr`,
  },
};

interface ChartRow { param: string; successRate: number; medianFinal: number }

function SensitivityChart({ data }: { data: ChartRow[] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis dataKey="param" tick={TICK_STYLE} stroke="#262626" />
          <YAxis yAxisId="left" tick={TICK_STYLE} stroke="#262626" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis yAxisId="right" orientation="right" tickFormatter={formatCurrency} tick={TICK_STYLE} stroke="#262626" width={70} />
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value, name) => {
            const v = Number(value ?? 0);
            const n = String(name);
            return n === "Success Rate" ? [`${v}%`, n] : [formatCurrency(v), n];
          }} />
          <Legend wrapperStyle={{ fontSize: "12px", color: "#a3a3a3" }} />
          <Line yAxisId="left" type="monotone" dataKey="successRate" stroke="#16a34a" strokeWidth={2} dot={{ r: 4 }} name="Success Rate" />
          <Line yAxisId="right" type="monotone" dataKey="medianFinal" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} name="Median Final Value" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SensitivityTable({ data, paramLabel }: { data: ChartRow[]; paramLabel: string }) {
  function rateColor(rate: number) {
    if (rate >= 90) return "text-success";
    if (rate >= 70) return "text-warning";
    return "text-destructive";
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-2 px-2 text-muted-foreground font-medium">{paramLabel}</th>
            <th className="text-right py-2 px-2 text-muted-foreground font-medium">Success Rate</th>
            <th className="text-right py-2 px-2 text-muted-foreground font-medium">Median Final</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-border/50">
              <td className="py-1.5 px-2 text-foreground">{row.param}</td>
              <td className={`py-1.5 px-2 text-right font-medium ${rateColor(row.successRate)}`}>{row.successRate}%</td>
              <td className="py-1.5 px-2 text-right text-foreground">{formatCurrency(row.medianFinal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SensitivityAnalysis() {
  const { config } = useSimulationStore();
  const sensitivity = useRunSensitivity();
  const [selectedParam, setSelectedParam] = useState<SensitivityParam>("withdrawal_rate");
  const paramInfo = PARAM_OPTIONS[selectedParam];

  function handleRun() {
    sensitivity.mutate({ ...config, vary_param: selectedParam, values: paramInfo.defaultValues });
  }

  const chartData: ChartRow[] = (sensitivity.data ?? []).map((r: SensitivityResult) => ({
    param: paramInfo.formatValue(r.param_value),
    successRate: Math.round(r.success_rate * 100),
    medianFinal: r.median_final_value,
  }));

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Sensitivity Analysis</h3>
      <p className="text-xs text-muted-foreground">Vary a single parameter to see how it affects FIRE success probability.</p>
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-muted-foreground mb-1">Parameter to Vary</label>
          <select value={selectedParam} onChange={(e) => setSelectedParam(e.target.value as SensitivityParam)} className="w-full px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
            {(Object.keys(PARAM_OPTIONS) as SensitivityParam[]).map((p) => (
              <option key={p} value={p}>{PARAM_OPTIONS[p].label}</option>
            ))}
          </select>
        </div>
        <button onClick={handleRun} disabled={sensitivity.isPending} className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
          {sensitivity.isPending ? "Analyzing..." : "Run Analysis"}
        </button>
      </div>
      {sensitivity.isError && (
        <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-destructive text-sm">{sensitivity.error.message}</div>
      )}
      {chartData.length > 0 && (
        <div className="space-y-4">
          <SensitivityChart data={chartData} />
          <SensitivityTable data={chartData} paramLabel={paramInfo.label} />
        </div>
      )}
    </div>
  );
}
