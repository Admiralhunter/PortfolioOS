/**
 * Base LLM provider implementation for OpenAI-compatible APIs.
 *
 * LM Studio, OpenAI, and OpenRouter all use the same OpenAI-compatible
 * chat completion API format, so they share this base implementation.
 */

import type {
  LLMProvider,
  LLMOptions,
  LLMResponse,
  ChatCompletionRequest,
  ChatCompletionResponse,
} from "./types";

export class OpenAICompatibleProvider implements LLMProvider {
  id: string;
  name: string;
  isLocal: boolean;
  private endpointUrl: string;
  private defaultModel: string;
  private apiKey: string;

  constructor(
    id: string,
    name: string,
    endpointUrl: string,
    model: string,
    isLocal: boolean,
    apiKey = ""
  ) {
    this.id = id;
    this.name = name;
    this.endpointUrl = endpointUrl.replace(/\/+$/, "");
    this.defaultModel = model;
    this.isLocal = isLocal;
    this.apiKey = apiKey;
  }

  async send(prompt: string, options?: LLMOptions): Promise<LLMResponse> {
    const model = options?.model ?? this.defaultModel;
    const messages: Array<{ role: string; content: string }> = [];

    if (options?.systemPrompt) {
      messages.push({ role: "system", content: options.systemPrompt });
    }
    messages.push({ role: "user", content: prompt });

    const body: ChatCompletionRequest = {
      model,
      messages,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.maxTokens ?? 2048,
    };

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(`${this.endpointUrl}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`LLM request failed (${response.status}): ${text}`);
    }

    const data = (await response.json()) as ChatCompletionResponse;
    const choice = data.choices?.[0];
    if (!choice) {
      throw new Error("No response from LLM provider");
    }

    return {
      content: choice.message.content,
      model: data.model,
      tokensUsed: {
        prompt: data.usage?.prompt_tokens ?? 0,
        completion: data.usage?.completion_tokens ?? 0,
      },
    };
  }

  async listModels(): Promise<string[]> {
    const headers: Record<string, string> = {};
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    try {
      const response = await fetch(`${this.endpointUrl}/models`, { headers });
      if (!response.ok) return [];
      const data = (await response.json()) as {
        data: Array<{ id: string }>;
      };
      return data.data?.map((m) => m.id) ?? [];
    } catch {
      return [];
    }
  }

  async testConnection(): Promise<boolean> {
    try {
      const models = await this.listModels();
      return models.length > 0;
    } catch {
      return false;
    }
  }
}
