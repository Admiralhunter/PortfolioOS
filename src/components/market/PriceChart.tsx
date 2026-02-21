/**
 * Price chart — candlestick chart using TradingView's Lightweight Charts v5.
 * Displays OHLCV data for a single symbol with volume histogram.
 */

import { useEffect, useRef } from "react";
import {
  createChart, CandlestickSeries, HistogramSeries,
  type IChartApi, type ISeriesApi, ColorType,
} from "lightweight-charts";
import type { PriceRecord } from "../../types";

const CHART_OPTIONS = {
  layout: { background: { type: ColorType.Solid, color: "#141414" }, textColor: "#a3a3a3", fontSize: 11 },
  grid: { vertLines: { color: "#1e1e1e" }, horzLines: { color: "#1e1e1e" } },
  crosshair: { vertLine: { color: "#3b82f6", width: 1 as const, style: 2 as const }, horzLine: { color: "#3b82f6", width: 1 as const, style: 2 as const } },
  rightPriceScale: { borderColor: "#262626" },
  timeScale: { borderColor: "#262626", timeVisible: false },
  height: 400,
};

function useChartSetup(containerRef: React.RefObject<HTMLDivElement | null>) {
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { ...CHART_OPTIONS, width: containerRef.current.clientWidth });
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#16a34a", downColor: "#dc2626",
      borderUpColor: "#16a34a", borderDownColor: "#dc2626",
      wickUpColor: "#16a34a", wickDownColor: "#dc2626",
    });
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chartRef.current = chart;
    candleRef.current = candle;
    volumeRef.current = volume;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) chart.applyOptions({ width: entry.contentRect.width });
    });
    observer.observe(containerRef.current);
    return () => { observer.disconnect(); chart.remove(); };
  }, [containerRef]);

  return { chartRef, candleRef, volumeRef };
}

function ChartHeader({ symbol, data }: { symbol: string; data: PriceRecord[] }) {
  const last = data.length > 0 ? data[data.length - 1] : null;
  return (
    <div className="flex items-center justify-between mb-3">
      <h4 className="text-sm font-semibold text-foreground">{symbol}</h4>
      {last && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Last: ${last.close.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          <span>{data.length} data points</span>
        </div>
      )}
    </div>
  );
}

export function PriceChart({ data, symbol }: { data: PriceRecord[]; symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { chartRef, candleRef, volumeRef } = useChartSetup(containerRef);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current || data.length === 0) return;
    const sorted = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    candleRef.current.setData(sorted.map((r) => ({ time: r.date as string, open: r.open, high: r.high, low: r.low, close: r.close })));
    volumeRef.current.setData(sorted.map((r) => ({ time: r.date as string, value: r.volume, color: r.close >= r.open ? "#16a34a40" : "#dc262640" })));
    chartRef.current?.timeScale().fitContent();
  }, [data, chartRef, candleRef, volumeRef]);

  return (
    <div>
      <ChartHeader symbol={symbol} data={data} />
      <div ref={containerRef} className="rounded-md overflow-hidden" />
    </div>
  );
}
