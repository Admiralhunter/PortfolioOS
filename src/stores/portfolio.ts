/**
 * Portfolio state store — selected account, active filters.
 */

import { create } from "zustand";

interface PortfolioState {
  selectedAccountId: string | null;
  setSelectedAccountId: (id: string | null) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  selectedAccountId: null,
  setSelectedAccountId: (id) => set({ selectedAccountId: id }),
}));
