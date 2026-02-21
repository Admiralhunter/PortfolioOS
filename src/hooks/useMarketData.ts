/**
 * TanStack Query hooks for market data operations via IPC.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

export function useFetchPriceHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      symbol,
      startDate,
      endDate,
    }: {
      symbol: string;
      startDate: string;
      endDate: string;
    }) => {
      const response = await window.api.market.fetchPriceHistory(
        symbol,
        startDate,
        endDate
      );
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["prices", variables.symbol],
      });
    },
  });
}

export function useFetchMacroSeries() {
  return useMutation({
    mutationFn: async ({
      seriesId,
      startDate,
      endDate,
    }: {
      seriesId: string;
      startDate: string;
      endDate: string;
    }) => {
      const response = await window.api.market.fetchMacroSeries(
        seriesId,
        startDate,
        endDate
      );
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
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
