/**
 * TanStack Query hook for fetching holdings via IPC.
 */

import { useQuery } from "@tanstack/react-query";

export function useHoldings(accountId?: string) {
  return useQuery({
    queryKey: ["holdings", accountId],
    queryFn: async () => {
      const response = await window.api.portfolio.getHoldings(accountId);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}
