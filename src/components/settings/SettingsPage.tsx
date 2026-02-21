/**
 * Settings page — LLM provider configuration and app preferences.
 */

import { useState } from "react";
import { LLMProviderSettings } from "./LLMProviderSettings";
import { AppPreferences } from "./AppPreferences";

type SettingsTab = "llm" | "preferences";

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("llm");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground">Settings</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Configure LLM providers and application preferences.
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-muted p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab("llm")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "llm"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          LLM Providers
        </button>
        <button
          onClick={() => setActiveTab("preferences")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "preferences"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Preferences
        </button>
      </div>

      {/* Content */}
      <div className="bg-card border border-border rounded-lg p-6">
        {activeTab === "llm" && <LLMProviderSettings />}
        {activeTab === "preferences" && <AppPreferences />}
      </div>
    </div>
  );
}
