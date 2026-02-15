/**
 * LLM provider type definitions.
 */

export interface LLMProviderConfig {
  id: string;
  name: string;
  providerType: string;
  endpointUrl: string;
  model: string;
  isLocal: boolean;
  apiKey?: string;
}

export interface LLMOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface LLMResponse {
  content: string;
  model: string;
  tokensUsed: { prompt: number; completion: number };
}

export interface LLMProvider {
  id: string;
  name: string;
  isLocal: boolean;
  send(prompt: string, options?: LLMOptions): Promise<LLMResponse>;
  listModels(): Promise<string[]>;
  testConnection(): Promise<boolean>;
}

/** OpenAI-compatible chat completion request body. */
export interface ChatCompletionRequest {
  model: string;
  messages: Array<{ role: string; content: string }>;
  temperature?: number;
  max_tokens?: number;
}

/** OpenAI-compatible chat completion response. */
export interface ChatCompletionResponse {
  choices: Array<{
    message: { content: string };
  }>;
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
