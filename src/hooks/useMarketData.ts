/**
 * TanStack Query hooks for market data operations via IPC.
 */

import { useQuery } from "@tanstack/react-query";

export function usePriceHistory(
  symbol: string,
  dateRange?: { start: string; end: string }
) {
  return useQuery({
    queryKey: ["prices", symbol, dateRange],
    queryFn: async () => {
      const response = await window.api.market.getCachedPrices(symbol, dateRange);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    enabled: !!symbol,
  });
}

export function useGapDetection(symbol: string) {
  return useQuery({
    queryKey: ["gaps", symbol],
    queryFn: async () => {
      const response = await window.api.market.detectGaps(symbol);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    enabled: !!symbol,
  });
}
