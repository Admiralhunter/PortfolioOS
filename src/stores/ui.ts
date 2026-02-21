/**
 * UI state store — sidebar state, active view, theme.
 */

import { create } from "zustand";

type View = "portfolio" | "fire" | "market" | "settings";
type Theme = "dark" | "light";

interface UIState {
  sidebarOpen: boolean;
  activeView: View;
  theme: Theme;
  toggleSidebar: () => void;
  setActiveView: (view: View) => void;
  setTheme: (theme: Theme) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  activeView: "portfolio",
  theme: "dark",
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveView: (view) => set({ activeView: view }),
  setTheme: (theme) => set({ theme }),
}));
