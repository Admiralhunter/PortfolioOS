/**
 * LLM provider settings — list, add, remove, and set default LLM providers.
 *
 * Supports LM Studio (local, default), OpenAI, Anthropic, and OpenRouter.
 * API keys are stored in the OS keychain via Electron safeStorage.
 */

import { useState } from "react";
import {
  useProviders, useAddProvider, useDeleteProvider, useSetDefaultProvider, useLLMSend,
} from "../../hooks/useLLM";
import type { LLMProvider, LLMProviderType } from "../../types";

const INPUT_CLASS = "w-full px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary";

const PROVIDER_DEFAULTS: Record<LLMProviderType, { endpoint: string; model: string; isLocal: boolean }> = {
  lmstudio: { endpoint: "http://localhost:1234/v1", model: "local-model", isLocal: true },
  openai: { endpoint: "https://api.openai.com/v1", model: "gpt-4o", isLocal: false },
  anthropic: { endpoint: "https://api.anthropic.com/v1", model: "claude-sonnet-4-20250514", isLocal: false },
  openrouter: { endpoint: "https://openrouter.ai/api/v1", model: "anthropic/claude-sonnet-4-20250514", isLocal: false },
};

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>{children}</div>;
}

function AddProviderForm({ onClose }: { onClose: () => void }) {
  const addProvider = useAddProvider();
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState<LLMProviderType>("lmstudio");
  const [endpoint, setEndpoint] = useState(PROVIDER_DEFAULTS.lmstudio.endpoint);
  const [model, setModel] = useState(PROVIDER_DEFAULTS.lmstudio.model);
  const [apiKey, setApiKey] = useState("");

  function handleTypeChange(type: LLMProviderType) {
    setProviderType(type);
    setEndpoint(PROVIDER_DEFAULTS[type].endpoint);
    setModel(PROVIDER_DEFAULTS[type].model);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await addProvider.mutateAsync({
      name: name || `${providerType} provider`, provider_type: providerType,
      endpoint_url: endpoint, model, is_local: PROVIDER_DEFAULTS[providerType].isLocal,
      api_key: apiKey || undefined,
    });
    onClose();
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 rounded-lg border border-primary/30 bg-primary/5 space-y-4">
      <h4 className="text-sm font-semibold text-foreground">Add LLM Provider</h4>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Name"><input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="My Provider" className={INPUT_CLASS} /></FormField>
        <FormField label="Provider Type">
          <select value={providerType} onChange={(e) => handleTypeChange(e.target.value as LLMProviderType)} className={INPUT_CLASS}>
            <option value="lmstudio">LM Studio (Local)</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="openrouter">OpenRouter</option>
          </select>
        </FormField>
      </div>
      <FormField label="Endpoint URL"><input type="url" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} className={INPUT_CLASS} /></FormField>
      <FormField label="Model"><input type="text" value={model} onChange={(e) => setModel(e.target.value)} className={INPUT_CLASS} /></FormField>
      {!PROVIDER_DEFAULTS[providerType].isLocal && (
        <FormField label="API Key">
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className={INPUT_CLASS} />
          <p className="text-xs text-muted-foreground mt-1">Stored in OS keychain via Electron safeStorage.</p>
        </FormField>
      )}
      {addProvider.isError && <p className="text-xs text-destructive">{addProvider.error.message}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={addProvider.isPending} className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">{addProvider.isPending ? "Adding..." : "Add Provider"}</button>
        <button type="button" onClick={onClose} className="px-4 py-2 rounded-md border border-border text-sm text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
      </div>
    </form>
  );
}

function TestConnection() {
  const send = useLLMSend();
  const [result, setResult] = useState<string | null>(null);
  async function handleTest() {
    setResult(null);
    try {
      const r = await send.mutateAsync({ prompt: "Reply with exactly: Connection successful", options: { maxTokens: 50, temperature: 0 } });
      setResult(`Connected: ${r.model} responded.`);
    } catch (err) { setResult(`Failed: ${(err as Error).message}`); }
  }
  return (
    <div className="flex items-center gap-3">
      <button onClick={handleTest} disabled={send.isPending} className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors">{send.isPending ? "Testing..." : "Test Connection"}</button>
      {result && <span className={`text-xs ${result.startsWith("Connected") ? "text-success" : "text-destructive"}`}>{result}</span>}
    </div>
  );
}

function ProviderCard({ provider, onSetDefault, onDelete }: {
  provider: LLMProvider; onSetDefault: () => void; onDelete: () => void;
}) {
  return (
    <div className={`p-4 rounded-lg border ${provider.is_default ? "border-primary bg-primary/5" : "border-border bg-card"}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-foreground">{provider.name}</p>
            {provider.is_default && <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">Default</span>}
            {provider.is_local && <span className="text-xs px-2 py-0.5 rounded-full bg-success/10 text-success">Local</span>}
          </div>
          <p className="text-xs text-muted-foreground mt-1">{provider.provider_type} &middot; {provider.model}</p>
          <p className="text-xs text-muted-foreground">{provider.endpoint_url}</p>
        </div>
        <div className="flex items-center gap-2">
          {!provider.is_default && <button onClick={onSetDefault} className="text-xs px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground transition-colors">Set Default</button>}
          <button onClick={onDelete} className="text-xs px-2 py-1 rounded border border-border text-muted-foreground hover:text-destructive hover:border-destructive/30 transition-colors">Remove</button>
        </div>
      </div>
    </div>
  );
}

export function LLMProviderSettings() {
  const { data: providers, isLoading, isError, error } = useProviders();
  const deleteProvider = useDeleteProvider();
  const setDefault = useSetDefaultProvider();
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">LLM Providers</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Configure language model providers for portfolio queries.</p>
        </div>
        <button onClick={() => setIsAdding(!isAdding)} className="text-xs text-primary hover:text-primary/80 transition-colors">{isAdding ? "Cancel" : "+ Add Provider"}</button>
      </div>
      {isAdding && <AddProviderForm onClose={() => setIsAdding(false)} />}
      {isLoading && <div className="animate-pulse space-y-2"><div className="h-16 bg-muted rounded" /><div className="h-16 bg-muted rounded" /></div>}
      {isError && <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-destructive text-sm">Failed to load providers: {error.message}</div>}
      {providers && providers.length === 0 && <div className="p-6 text-center text-muted-foreground text-sm">No providers configured. Add one to enable AI features.</div>}
      {providers && providers.length > 0 && (
        <div className="space-y-2">
          {providers.map((p) => <ProviderCard key={p.id} provider={p} onSetDefault={() => setDefault.mutate(p.id)} onDelete={() => deleteProvider.mutate(p.id)} />)}
        </div>
      )}
      <div className="pt-2 border-t border-border"><TestConnection /></div>
      <div className="p-3 rounded-md bg-muted text-xs text-muted-foreground space-y-1">
        <p className="font-medium text-foreground">Privacy Notice</p>
        <p>LM Studio (local) has full data access. Cloud providers require explicit consent before portfolio data is shared.</p>
      </div>
    </div>
  );
}
