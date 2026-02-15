/**
 * OpenAI provider — cloud LLM, API key required.
 *
 * Requires explicit user consent before sending any portfolio data.
 * API key stored/retrieved via Electron safeStorage.
 */

import { OpenAICompatibleProvider } from "./provider";

const DEFAULT_ENDPOINT = "https://api.openai.com/v1";

export function createOpenAIProvider(
  id: string,
  name = "OpenAI",
  model = "gpt-4o",
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
