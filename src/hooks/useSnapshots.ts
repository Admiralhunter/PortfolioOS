/**
 * TanStack Query hook for fetching portfolio snapshots via IPC.
 */

import { useQuery } from "@tanstack/react-query";

export function useSnapshots(
  accountId: string | null,
  dateRange?: { start: string; end: string }
) {
  return useQuery({
    queryKey: ["snapshots", accountId, dateRange],
    queryFn: async () => {
      if (!accountId) return [];
      const response = await window.api.portfolio.getSnapshots(accountId, dateRange);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    enabled: !!accountId,
  });
}
