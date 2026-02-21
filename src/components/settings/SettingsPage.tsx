/**
 * Settings page — app preferences and LLM provider configuration.
 */

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-foreground">Settings</h2>
      <div className="bg-card border border-border rounded-lg p-8 text-center">
        <p className="text-muted-foreground">
          LLM provider settings and app preferences coming soon.
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Configure LM Studio (local), OpenAI, Anthropic, or OpenRouter.
        </p>
      </div>
    </div>
  );
}
