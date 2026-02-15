/**
 * LM Studio provider — local inference, no API key required.
 *
 * Default endpoint: http://localhost:1234/v1 (LM Studio default).
 * Full data access — no consent prompts since everything stays local.
 */

import { OpenAICompatibleProvider } from "./provider";

const DEFAULT_ENDPOINT = "http://localhost:1234/v1";

export function createLMStudioProvider(
  id = "lmstudio-default",
  name = "LM Studio (Local)",
  endpointUrl = DEFAULT_ENDPOINT,
  model = ""
): OpenAICompatibleProvider {
  return new OpenAICompatibleProvider(
    id,
    name,
    endpointUrl,
    model,
    true, // isLocal
    ""   // no API key
  );
}
