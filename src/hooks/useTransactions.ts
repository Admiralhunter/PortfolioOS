/**
 * TanStack Query hook for fetching transactions via IPC.
 */

import { useQuery } from "@tanstack/react-query";
import type { TransactionFilters } from "../types";

export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: async () => {
      const response = await window.api.portfolio.getTransactions(filters);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}
