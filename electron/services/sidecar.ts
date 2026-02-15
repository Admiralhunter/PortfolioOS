/**
 * Python sidecar process manager.
 *
 * Spawns and manages the Python analytics sidecar process, handling
 * stdin/stdout JSON communication, request correlation, timeouts,
 * and crash recovery with backoff.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { v4 as uuidv4 } from "uuid";
import * as path from "node:path";

/** Default timeout for sidecar requests (30s for simulations). */
const DEFAULT_TIMEOUT_MS = 30_000;

/** Maximum restart attempts before giving up. */
const MAX_RESTART_ATTEMPTS = 5;

/** Backoff multiplier for restarts. */
const RESTART_BACKOFF_MS = 2_000;

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export class SidecarManager {
  private process: ChildProcess | null = null;
  private pending: Map<string, PendingRequest> = new Map();
  private buffer = "";
  private restartAttempts = 0;
  private running = false;
  private pythonDir: string;
  private requestQueue: Array<{
    id: string;
    payload: string;
    resolve: (value: unknown) => void;
    reject: (reason: Error) => void;
    timeoutMs: number;
  }> = [];
  private processing = false;

  constructor(pythonDir?: string) {
    this.pythonDir =
      pythonDir ?? path.join(process.cwd(), "python");
  }

  /** Start the Python sidecar process. */
  start(): void {
    if (this.running) return;

    this.process = spawn("uv", ["run", "python", "-m", "portfolioos.main"], {
      cwd: this.pythonDir,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env },
    });

    this.running = true;
    this.restartAttempts = 0;

    this.process.stdout?.on("data", (data: Buffer) => {
      this.handleStdout(data.toString());
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      console.error("[sidecar stderr]", data.toString().trim());
    });

    this.process.on("exit", (code, signal) => {
      this.running = false;
      console.error(
        `[sidecar] Process exited with code=${code} signal=${signal}`
      );

      // Reject all pending requests
      for (const [id, req] of this.pending) {
        clearTimeout(req.timer);
        req.reject(new Error(`Sidecar process exited (code=${code})`));
        this.pending.delete(id);
      }

      // Auto-restart with backoff if not intentionally stopped
      if (code !== 0 && this.restartAttempts < MAX_RESTART_ATTEMPTS) {
        this.restartAttempts++;
        const delay = RESTART_BACKOFF_MS * this.restartAttempts;
        console.error(
          `[sidecar] Restarting in ${delay}ms (attempt ${this.restartAttempts})`
        );
        setTimeout(() => this.start(), delay);
      }
    });

    this.process.on("error", (err) => {
      console.error("[sidecar] Spawn error:", err.message);
      this.running = false;
    });
  }

  /** Stop the sidecar process gracefully. */
  stop(): void {
    if (!this.process) return;

    this.running = false;
    this.restartAttempts = MAX_RESTART_ATTEMPTS; // Prevent auto-restart

    // Close stdin to signal EOF
    this.process.stdin?.end();

    // Give it a moment to exit gracefully, then force kill
    const killTimer = setTimeout(() => {
      if (this.process && !this.process.killed) {
        this.process.kill("SIGKILL");
      }
    }, 5_000);

    this.process.on("exit", () => {
      clearTimeout(killTimer);
    });

    this.process.kill("SIGTERM");
    this.process = null;
  }

  /** Restart the sidecar process. */
  restart(): void {
    this.stop();
    setTimeout(() => {
      this.restartAttempts = 0;
      this.start();
    }, 1_000);
  }

  /** Check if the sidecar process is running. */
  isRunning(): boolean {
    return this.running && this.process !== null && !this.process.killed;
  }

  /**
   * Send a JSON-RPC request to the sidecar and await the response.
   *
   * Requests are queued and processed sequentially since the Python
   * sidecar reads stdin line by line.
   */
  async send(
    method: string,
    params: Record<string, unknown> = {},
    timeoutMs: number = DEFAULT_TIMEOUT_MS
  ): Promise<unknown> {
    if (!this.isRunning()) {
      throw new Error("Sidecar is not running");
    }

    const id = uuidv4();
    const payload = JSON.stringify({ id, method, params }) + "\n";

    return new Promise((resolve, reject) => {
      this.requestQueue.push({ id, payload, resolve, reject, timeoutMs });
      this.processQueue();
    });
  }

  /** Process the next request in the queue. */
  private processQueue(): void {
    if (this.processing || this.requestQueue.length === 0) return;

    this.processing = true;
    const req = this.requestQueue.shift()!;

    const timer = setTimeout(() => {
      this.pending.delete(req.id);
      this.processing = false;
      req.reject(new Error(`Sidecar request timed out after ${req.timeoutMs}ms`));
      this.processQueue();
    }, req.timeoutMs);

    this.pending.set(req.id, {
      resolve: (value: unknown) => {
        req.resolve(value);
        this.processing = false;
        this.processQueue();
      },
      reject: (reason: Error) => {
        req.reject(reason);
        this.processing = false;
        this.processQueue();
      },
      timer,
    });

    try {
      this.process!.stdin!.write(req.payload);
    } catch (err) {
      clearTimeout(timer);
      this.pending.delete(req.id);
      this.processing = false;
      req.reject(
        new Error(`Failed to write to sidecar: ${(err as Error).message}`)
      );
      this.processQueue();
    }
  }

  /** Handle stdout data from the sidecar, buffering partial lines. */
  private handleStdout(data: string): void {
    this.buffer += data;
    const lines = this.buffer.split("\n");
    // Keep the last incomplete line in the buffer
    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        const response = JSON.parse(trimmed) as {
          id: string;
          result?: unknown;
          error?: { message: string; traceback?: string };
        };

        const pending = this.pending.get(response.id);
        if (!pending) continue;

        clearTimeout(pending.timer);
        this.pending.delete(response.id);

        if (response.error) {
          pending.reject(new Error(response.error.message));
        } else {
          pending.resolve(response.result);
        }
      } catch {
        console.error("[sidecar] Failed to parse response:", trimmed);
      }
    }
  }
}
