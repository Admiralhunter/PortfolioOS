/**
 * LLM provider manager — registry and routing.
 *
 * Manages configured LLM providers, handles provider creation,
 * and routes requests to the correct provider (default or specified).
 *
 * Privacy rule: local LM Studio can access all data; cloud providers
 * require explicit user consent per interaction or global opt-in.
 */

import type { LLMProvider, LLMOptions, LLMResponse } from "./types";
import { createLMStudioProvider } from "./lmstudio";
import { createOpenAIProvider } from "./openai";
import { createAnthropicProvider } from "./anthropic";
import { createOpenRouterProvider } from "./openrouter";
import {
  addLLMProvider as dbAddProvider,
  removeProvider as dbRemoveProvider,
  getLLMProviders,
  setDefaultProvider,
} from "../db/sqlite";
import { storeKey, getKey, deleteKey } from "../services/keychain";

export class LLMManager {
  private providers: Map<string, LLMProvider> = new Map();

  constructor() {
    // Always register the default LM Studio provider
    const lmstudio = createLMStudioProvider();
    this.providers.set(lmstudio.id, lmstudio);
  }

  /** Get a provider by ID, or the default provider. */
  getProvider(id?: string): LLMProvider {
    if (id) {
      const provider = this.providers.get(id);
      if (!provider) {
        throw new Error(`LLM provider '${id}' not found`);
      }
      return provider;
    }

    // Find the default provider from database config
    const configs = getLLMProviders();
    const defaultConfig = configs.find((c) => c.is_default);
    if (defaultConfig) {
      const provider = this.providers.get(defaultConfig.id);
      if (provider) return provider;
    }

    // Fall back to LM Studio
    const lmstudio = this.providers.get("lmstudio-default");
    if (lmstudio) return lmstudio;

    throw new Error("No LLM providers configured");
  }

  /** Send a prompt to the default (or specified) provider. */
  async send(prompt: string, options?: LLMOptions): Promise<LLMResponse> {
    const provider = this.getProvider();

    // Cloud provider consent check
    if (!provider.isLocal) {
      // In production, this would check user preferences
      // For now, cloud providers must have been explicitly configured
      console.warn(
        `[llm] Sending to cloud provider '${provider.name}'. ` +
          "Ensure user has opted in."
      );
    }

    return provider.send(prompt, options);
  }

  /** Add a new provider configuration. */
  async addProvider(config: {
    name: string;
    provider_type: string;
    endpoint_url: string;
    model: string;
    is_local: boolean;
    api_key?: string;
  }): Promise<{ id: string; name: string }> {
    // Store in SQLite
    const dbRecord = dbAddProvider(
      config.name,
      config.provider_type,
      config.endpoint_url,
      config.model,
      config.is_local
    );

    // Store API key securely if provided
    if (config.api_key) {
      const keyRef = `${config.provider_type}-api-key`;
      storeKey(keyRef, config.api_key);
    }

    // Create the provider instance
    const apiKey = config.api_key ?? "";
    const provider = this.createProviderInstance(
      dbRecord.id,
      config.name,
      config.provider_type,
      config.endpoint_url,
      config.model,
      config.is_local,
      apiKey
    );
    this.providers.set(dbRecord.id, provider);

    return { id: dbRecord.id, name: config.name };
  }

  /** Remove a provider and its API key. */
  removeProvider(id: string): boolean {
    // Look up the provider type to delete the associated API key
    const configs = getLLMProviders();
    const config = configs.find((c) => c.id === id);
    if (config && !config.is_local) {
      const keyRef = `${config.provider_type}-api-key`;
      deleteKey(keyRef);
    }

    this.providers.delete(id);
    return dbRemoveProvider(id);
  }

  /** Set a provider as the default. */
  setDefault(id: string): boolean {
    return setDefaultProvider(id);
  }

  /** Get all configured providers. */
  getAll(): Array<{ id: string; name: string; isLocal: boolean; isDefault: boolean }> {
    const configs = getLLMProviders();
    return configs.map((c) => ({
      id: c.id,
      name: c.name,
      isLocal: c.is_local,
      isDefault: c.is_default,
    }));
  }

  /** Load providers from database on startup. */
  loadFromDB(): void {
    const configs = getLLMProviders();
    for (const config of configs) {
      if (this.providers.has(config.id)) continue;

      let apiKey = "";
      if (!config.is_local) {
        const keyRef = `${config.provider_type}-api-key`;
        apiKey = getKey(keyRef) ?? "";
      }

      const provider = this.createProviderInstance(
        config.id,
        config.name,
        config.provider_type,
        config.endpoint_url,
        config.model,
        config.is_local,
        apiKey
      );
      this.providers.set(config.id, provider);
    }
  }

  private createProviderInstance(
    id: string,
    name: string,
    providerType: string,
    endpointUrl: string,
    model: string,
    isLocal: boolean,
    apiKey: string
  ): LLMProvider {
    switch (providerType) {
      case "lmstudio":
        return createLMStudioProvider(id, name, endpointUrl, model);
      case "openai":
        return createOpenAIProvider(id, name, model, apiKey);
      case "anthropic":
        return createAnthropicProvider(id, name, model, apiKey);
      case "openrouter":
        return createOpenRouterProvider(id, name, model, apiKey);
      default: {
        // Generic OpenAI-compatible provider
        const { OpenAICompatibleProvider } = require("./provider");
        return new OpenAICompatibleProvider(
          id,
          name,
          endpointUrl,
          model,
          isLocal,
          apiKey
        );
      }
    }
  }
}
