/**
 * Tests for the Python sidecar manager.
 *
 * Tests the SidecarManager class with a real Python sidecar process
 * to verify end-to-end communication.
 */

import { describe, it, expect, afterEach } from "vitest";
import * as path from "node:path";
import { SidecarManager } from "../../../electron/services/sidecar";

const PYTHON_DIR = path.join(process.cwd(), "python");

let sidecar: SidecarManager | null = null;

afterEach(() => {
  if (sidecar) {
    sidecar.stop();
    sidecar = null;
  }
});

describe("SidecarManager", () => {
  it("starts and reports running", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    sidecar.start();
    // Give it a moment to spawn
    await new Promise((r) => setTimeout(r, 2000));
    expect(sidecar.isRunning()).toBe(true);
  });

  it("stops cleanly", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    sidecar.start();
    await new Promise((r) => setTimeout(r, 2000));
    sidecar.stop();
    await new Promise((r) => setTimeout(r, 1000));
    expect(sidecar.isRunning()).toBe(false);
    sidecar = null; // Already stopped
  });

  it("sends a request and receives a response", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    sidecar.start();
    await new Promise((r) => setTimeout(r, 2000));

    const result = await sidecar.send("analysis.cagr", {
      start_value: 100,
      end_value: 200,
      n_years: 10,
    });
    expect(result).toBeTypeOf("number");
    expect(result).toBeCloseTo(0.0718, 3); // CAGR of 100→200 in 10 years
  });

  it("handles unknown method error", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    sidecar.start();
    await new Promise((r) => setTimeout(r, 2000));

    await expect(
      sidecar.send("nonexistent.method", {})
    ).rejects.toThrow("Unknown method");
  });

  it("handles concurrent requests sequentially", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    sidecar.start();
    await new Promise((r) => setTimeout(r, 2000));

    const [r1, r2] = await Promise.all([
      sidecar.send("analysis.cagr", {
        start_value: 100,
        end_value: 200,
        n_years: 10,
      }),
      sidecar.send("analysis.cagr", {
        start_value: 100,
        end_value: 300,
        n_years: 10,
      }),
    ]);
    expect(r1).toBeTypeOf("number");
    expect(r2).toBeTypeOf("number");
    // 200/100 vs 300/100 — second should be higher CAGR
    expect(r2 as number).toBeGreaterThan(r1 as number);
  });

  it("rejects when sidecar is not running", async () => {
    sidecar = new SidecarManager(PYTHON_DIR);
    // Don't start it
    await expect(
      sidecar.send("analysis.cagr", { start_value: 100, end_value: 200, n_years: 10 })
    ).rejects.toThrow("not running");
  });
});
