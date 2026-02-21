/**
 * IPC handlers for LLM provider operations.
 *
 * Routes LLM configuration to SQLite and LLM requests to the
 * appropriate provider via the LLM manager.
 */

import { ipcMain, type IpcMainInvokeEvent } from "electron";
import type { IPCResponse } from "../types";
import type { LLMOptions as LLMRequestOptions } from "../llm/types";
import { getLLMProviders, setDefaultProvider } from "../db/sqlite";
import type { LLMManager } from "../llm/manager";

export function registerLLMHandlers(llmManager: LLMManager): void {
  ipcMain.handle(
    "llm:list-providers",
    async (): Promise<IPCResponse<unknown>> => {
      try {
        return { success: true, data: getLLMProviders() };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "llm:set-default",
    async (_event, providerId: string): Promise<IPCResponse<unknown>> => {
      try {
        const success = setDefaultProvider(providerId);
        if (!success) {
          return { success: false, error: `Provider ${providerId} not found` };
        }
        return { success: true };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "llm:send",
    async (_event: IpcMainInvokeEvent, prompt: string, options?: LLMRequestOptions): Promise<IPCResponse<unknown>> => {
      try {
        const response = await llmManager.send(prompt, options);
        return { success: true, data: response };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "llm:add-provider",
    async (_event: IpcMainInvokeEvent, config: { name: string; provider_type: string; endpoint_url: string; model: string; is_local: boolean; api_key?: string }): Promise<IPCResponse<unknown>> => {
      try {
        const provider = await llmManager.addProvider(config);
        return { success: true, data: provider };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "llm:delete-provider",
    async (_event, providerId: string): Promise<IPCResponse<unknown>> => {
      try {
        const success = llmManager.removeProvider(providerId);
        if (!success) {
          return { success: false, error: `Provider ${providerId} not found` };
        }
        return { success: true };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
