/**
 * Anthropic provider — cloud LLM, API key required.
 *
 * Uses the Anthropic Messages API format, which differs from OpenAI.
 * Requires explicit user consent before sending portfolio data.
 */

import type { LLMProvider, LLMOptions, LLMResponse } from "./types";

const DEFAULT_ENDPOINT = "https://api.anthropic.com/v1";

interface AnthropicMessageResponse {
  content: Array<{ text: string }>;
  model: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

export class AnthropicProvider implements LLMProvider {
  id: string;
  name: string;
  isLocal = false;
  private endpointUrl: string;
  private defaultModel: string;
  private apiKey: string;

  constructor(
    id: string,
    name = "Anthropic",
    model = "claude-sonnet-4-20250514",
    apiKey = ""
  ) {
    this.id = id;
    this.name = name;
    this.endpointUrl = DEFAULT_ENDPOINT;
    this.defaultModel = model;
    this.apiKey = apiKey;
  }

  async send(prompt: string, options?: LLMOptions): Promise<LLMResponse> {
    const model = options?.model ?? this.defaultModel;

    const body: Record<string, unknown> = {
      model,
      max_tokens: options?.maxTokens ?? 2048,
      messages: [{ role: "user", content: prompt }],
    };

    if (options?.systemPrompt) {
      body.system = options.systemPrompt;
    }
    if (options?.temperature !== undefined) {
      body.temperature = options.temperature;
    }

    const response = await fetch(`${this.endpointUrl}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": this.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Anthropic request failed (${response.status}): ${text}`);
    }

    const data = (await response.json()) as AnthropicMessageResponse;
    const content = data.content?.[0]?.text ?? "";

    return {
      content,
      model: data.model,
      tokensUsed: {
        prompt: data.usage?.input_tokens ?? 0,
        completion: data.usage?.output_tokens ?? 0,
      },
    };
  }

  async listModels(): Promise<string[]> {
    // Anthropic doesn't expose a models endpoint
    return [this.defaultModel];
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.endpointUrl}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": this.apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: this.defaultModel,
          max_tokens: 10,
          messages: [{ role: "user", content: "test" }],
        }),
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

export function createAnthropicProvider(
  id: string,
  name = "Anthropic",
  model = "claude-sonnet-4-20250514",
  apiKey = ""
): AnthropicProvider {
  return new AnthropicProvider(id, name, model, apiKey);
}
