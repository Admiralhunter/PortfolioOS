/**
 * OpenRouter provider — cloud LLM gateway, API key required.
 *
 * OpenRouter provides access to multiple models through a single
 * OpenAI-compatible endpoint. Requires explicit user consent.
 */

import { OpenAICompatibleProvider } from "./provider";

const DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1";

export function createOpenRouterProvider(
  id: string,
  name = "OpenRouter",
  model = "anthropic/claude-sonnet-4-20250514",
  apiKey = ""
): OpenAICompatibleProvider {
  return new OpenAICompatibleProvider(
    id,
    name,
    DEFAULT_ENDPOINT,
    model,
    false, // not local
    apiKey
  );
}
