/**
 * App preferences — theme, data paths, general application settings.
 */

import { useUIStore } from "../../stores/ui";
import { usePreferences, useSetPreference } from "../../hooks/usePreferences";
import type { Preferences } from "../../types";

function ThemeButton({ active, label, hint, onClick }: {
  active: boolean; label: string; hint: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} className={`flex-1 p-3 rounded-md border text-sm transition-colors ${active ? "border-primary bg-primary/5 text-foreground" : "border-border bg-muted text-muted-foreground hover:text-foreground"}`}>
      <span className="block font-medium">{label}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </button>
  );
}

function StoredPreferences({ prefs }: { prefs: Preferences }) {
  const entries = Object.entries(prefs);
  if (entries.length === 0) return null;
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-2">Stored Preferences</label>
      <div className="bg-muted rounded-md p-3 space-y-1">
        {entries.map(([key, value]) => (
          <div key={key} className="flex justify-between text-xs">
            <span className="text-muted-foreground font-mono">{key}</span>
            <span className="text-foreground">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AboutSection() {
  return (
    <>
      <div className="pt-4 border-t border-border">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">About</h4>
        <div className="space-y-1 text-xs text-muted-foreground">
          <p><span className="font-medium text-foreground">PortfolioOS</span> v0.1.0</p>
          <p>Local-first, privacy-preserving desktop application for personal finance management and FIRE analysis.</p>
          <p>License: PolyForm Noncommercial 1.0.0</p>
        </div>
      </div>
      <div className="p-3 rounded-md bg-muted text-xs text-muted-foreground space-y-1">
        <p className="font-medium text-foreground">Data Storage</p>
        <p>All data is stored locally. DuckDB handles analytics; SQLite stores preferences.</p>
        <p>No data is sent externally unless you enable cloud LLM providers and consent.</p>
      </div>
    </>
  );
}

export function AppPreferences() {
  const { theme, setTheme } = useUIStore();
  const { data: preferences, isLoading } = usePreferences();
  const setPreference = useSetPreference();

  function handleThemeChange(newTheme: "dark" | "light") {
    setTheme(newTheme);
    setPreference.mutate({ key: "theme", value: newTheme });
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-foreground">Application Preferences</h3>
        <p className="text-xs text-muted-foreground mt-0.5">General settings for the PortfolioOS application.</p>
      </div>
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">Theme</label>
        <div className="flex gap-2">
          <ThemeButton active={theme === "dark"} label="Dark" hint="Easy on the eyes" onClick={() => handleThemeChange("dark")} />
          <ThemeButton active={theme === "light"} label="Light" hint="High contrast" onClick={() => handleThemeChange("light")} />
        </div>
      </div>
      {isLoading && <div className="animate-pulse h-20 bg-muted rounded" />}
      {preferences && <StoredPreferences prefs={preferences} />}
      <AboutSection />
    </div>
  );
}
