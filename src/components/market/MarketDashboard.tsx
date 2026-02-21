/**
 * Market Intelligence dashboard — price charts for individual symbols
 * and macro economic indicators from FRED.
 *
 * Data sources: Yahoo Finance (price history), FRED (macro indicators).
 */

import { useState } from "react";
import { PriceChart } from "./PriceChart";
import { MacroIndicators } from "./MacroIndicators";
import { usePriceHistory, useFetchPriceHistory, useGapDetection } from "../../hooks/useMarketData";

function SymbolSearch({
  onSearch,
  isLoading,
}: {
  onSearch: (symbol: string, start: string, end: string) => void;
  isLoading: boolean;
}) {
  const [symbol, setSymbol] = useState("SPY");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate] = useState(new Date().toISOString().split("T")[0]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (symbol.trim()) {
      onSearch(symbol.trim().toUpperCase(), startDate, endDate);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          Symbol
        </label>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="e.g., SPY, VTI, AAPL"
          className="w-32 px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          Start Date
        </label>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          End Date
        </label>
        <input
          type="date"
          value={endDate}
          disabled
          className="px-3 py-2 bg-muted border border-border rounded-md text-sm text-muted-foreground cursor-not-allowed"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !symbol.trim()}
        className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? "Fetching..." : "Fetch Data"}
      </button>
    </form>
  );
}

function GapDetection({ symbol }: { symbol: string }) {
  const { data: gaps, isLoading } = useGapDetection(symbol);

  if (isLoading || !gaps) return null;
  if (gaps.length === 0) {
    return (
      <p className="text-xs text-success">
        No data gaps detected for {symbol}.
      </p>
    );
  }

  return (
    <div className="text-xs">
      <p className="text-warning font-medium">
        {gaps.length} data gap{gaps.length !== 1 ? "s" : ""} detected:
      </p>
      <div className="flex flex-wrap gap-2 mt-1">
        {gaps.slice(0, 5).map((gap, i) => (
          <span
            key={i}
            className="px-2 py-0.5 rounded bg-warning/10 text-warning"
          >
            {gap.expected_date} ({gap.gap_type})
          </span>
        ))}
        {gaps.length > 5 && (
          <span className="text-muted-foreground">
            +{gaps.length - 5} more
          </span>
        )}
      </div>
    </div>
  );
}

export function MarketDashboard() {
  const fetchPrices = useFetchPriceHistory();
  const [activeSymbol, setActiveSymbol] = useState("");
  const { data: cachedPrices } = usePriceHistory(activeSymbol);

  function handleSearch(symbol: string, start: string, end: string) {
    setActiveSymbol(symbol);
    fetchPrices.mutate({ symbol, startDate: start, endDate: end });
  }

  const priceData = cachedPrices ?? fetchPrices.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground">
          Market Intelligence
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Price charts and macro economic indicators. Powered by Yahoo Finance
          and FRED.
        </p>
      </div>

      {/* Price chart section */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-4">
        <h3 className="text-sm font-semibold text-foreground">Price Chart</h3>
        <SymbolSearch
          onSearch={handleSearch}
          isLoading={fetchPrices.isPending}
        />

        {fetchPrices.isError && (
          <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-destructive text-sm">
            Failed to fetch price data: {fetchPrices.error.message}
          </div>
        )}

        {priceData.length > 0 && (
          <>
            <PriceChart data={priceData} symbol={activeSymbol} />
            <GapDetection symbol={activeSymbol} />
          </>
        )}

        {activeSymbol && priceData.length === 0 && !fetchPrices.isPending && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            No cached price data for {activeSymbol}. Click Fetch Data to
            download.
          </div>
        )}

        {!activeSymbol && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            Enter a symbol and click Fetch Data to display a candlestick chart.
          </div>
        )}
      </div>

      {/* Macro indicators section */}
      <MacroIndicators />
    </div>
  );
}
