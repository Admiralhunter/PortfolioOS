/**
 * Macro indicators dashboard — FRED economic data display.
 * Shows key macro series: fed funds rate, CPI, unemployment, treasury yields.
 */

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useFetchMacroSeries } from "../../hooks/useMarketData";
import type { MacroRecord } from "../../types";

interface MacroSeries {
  id: string; label: string; unit: string; color: string;
}

const MACRO_SERIES: MacroSeries[] = [
  { id: "FEDFUNDS", label: "Fed Funds Rate", unit: "%", color: "#3b82f6" },
  { id: "CPIAUCSL", label: "CPI (All Urban)", unit: "Index", color: "#f59e0b" },
  { id: "UNRATE", label: "Unemployment Rate", unit: "%", color: "#dc2626" },
  { id: "DGS10", label: "10Y Treasury", unit: "%", color: "#16a34a" },
  { id: "DGS2", label: "2Y Treasury", unit: "%", color: "#8b5cf6" },
  { id: "MORTGAGE30US", label: "30Y Mortgage", unit: "%", color: "#ec4899" },
];

const TOOLTIP_STYLE = {
  backgroundColor: "#141414", border: "1px solid #262626",
  borderRadius: "6px", color: "#fafafa", fontSize: "12px",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function MacroChart({ data, series }: { data: MacroRecord[]; series: MacroSeries }) {
  if (data.length === 0) return null;
  const chartData = data.map((r) => ({ date: r.date, value: r.value }));
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fill: "#a3a3a3", fontSize: 10 }} stroke="#262626" />
          <YAxis tick={{ fill: "#a3a3a3", fontSize: 10 }} stroke="#262626" width={50} tickFormatter={(v) => series.unit === "%" ? `${v}%` : v.toLocaleString()} />
          <Tooltip formatter={(value) => { const v = Number(value ?? 0); return [series.unit === "%" ? `${v.toFixed(2)}%` : v.toLocaleString(), series.label]; }} labelFormatter={(label) => new Date(String(label)).toLocaleDateString()} contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey="value" stroke={series.color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function MacroCard({ series, data, isLoading, onFetch }: {
  series: MacroSeries; data?: MacroRecord[]; isLoading: boolean; onFetch: () => void;
}) {
  const lastValue = data?.[data.length - 1];
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-foreground">{series.label}</p>
          {lastValue && (
            <p className="text-xs text-muted-foreground">
              Latest: {series.unit === "%" ? `${lastValue.value.toFixed(2)}%` : lastValue.value.toLocaleString()} ({formatDate(lastValue.date)})
            </p>
          )}
        </div>
        {!data && (
          <button onClick={onFetch} disabled={isLoading} className="text-xs px-3 py-1 rounded-md border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground/30 disabled:opacity-50 transition-colors">
            {isLoading ? "Loading..." : "Fetch"}
          </button>
        )}
      </div>
      {isLoading && !data && (
        <div className="h-48 flex items-center justify-center">
          <div className="animate-pulse space-y-2 w-full">
            <div className="h-2 bg-muted rounded w-full" />
            <div className="h-2 bg-muted rounded w-3/4" />
          </div>
        </div>
      )}
      {data && <MacroChart data={data} series={series} />}
      {!data && !isLoading && (
        <div className="h-48 flex items-center justify-center text-xs text-muted-foreground">
          Click Fetch to load {series.label} data
        </div>
      )}
    </div>
  );
}

export function MacroIndicators() {
  const fetchMacro = useFetchMacroSeries();
  const [seriesData, setSeriesData] = useState<Record<string, MacroRecord[]>>({});
  const [loadingSeries, setLoadingSeries] = useState<Set<string>>(new Set());
  const dateRange = { start: "2020-01-01", end: new Date().toISOString().split("T")[0] };

  async function handleFetch(seriesId: string) {
    setLoadingSeries((prev) => new Set(prev).add(seriesId));
    try {
      const data = await fetchMacro.mutateAsync({ seriesId, startDate: dateRange.start, endDate: dateRange.end });
      setSeriesData((prev) => ({ ...prev, [seriesId]: data }));
    } catch { /* error surfaced in mutation state */ }
    finally {
      setLoadingSeries((prev) => { const next = new Set(prev); next.delete(seriesId); return next; });
    }
  }

  function handleFetchAll() {
    for (const s of MACRO_SERIES) { if (!seriesData[s.id]) handleFetch(s.id); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Macro Economic Indicators</h3>
        <button onClick={handleFetchAll} disabled={loadingSeries.size > 0} className="text-xs text-primary hover:text-primary/80 disabled:opacity-50 transition-colors">
          {loadingSeries.size > 0 ? "Loading..." : "Fetch All"}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">Federal Reserve Economic Data (FRED). Click a card to fetch data.</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {MACRO_SERIES.map((s) => (
          <MacroCard key={s.id} series={s} data={seriesData[s.id]} isLoading={loadingSeries.has(s.id)} onFetch={() => handleFetch(s.id)} />
        ))}
      </div>
    </div>
  );
}
