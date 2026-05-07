import { describe, expect, it } from "bun:test";

import {
  chromiumSetupFailureMessage,
  runCompatibilityGate,
  type GateCommand,
} from "../scripts/compatibilityGate";

describe("liepin bun compatibility gate", () => {
  it("runs local Playwright session checks without contacting Liepin", async () => {
    const result = await runCompatibilityGate({
      verifyProjectCommands: false,
      commandRunner: async (command: GateCommand) => {
        throw new Error(`unexpected shell command: ${command.join(" ")}`);
      },
    });

    expect(result.ok).toBe(true);
    expect(result.checks.map((check) => check.name)).toEqual([
      "playwright-chromium-installed",
      "playwright-chromium-launch",
      "persistent-context",
      "local-navigation",
      "passive-response-capture",
      "detail-command",
      "encrypted-session-reload",
      "crash-plaintext-check",
      "redaction",
    ]);
    expect(JSON.stringify(result)).not.toContain("liepin.com");
    expect(JSON.stringify(result)).not.toContain("devtools");
  });

  it("verifies the lockfile, Bun tests, and typecheck through project commands", async () => {
    const commands: GateCommand[] = [];

    const result = await runCompatibilityGate({
      verifyBrowserChecks: false,
      commandRunner: async (command: GateCommand) => {
        commands.push(command);
      },
    });

    expect(result.ok).toBe(true);
    expect(commands).toEqual([
      ["bun", "ci"],
      ["bun", "test", "--path-ignore-patterns", "tests/compatibility-gate.test.ts"],
      ["bun", "run", "typecheck"],
    ]);
    expect(result.checks.map((check) => check.name)).toEqual(["bun-ci", "bun-test", "typecheck"]);
  });

  it("names the Chromium setup command when browser binaries are missing", () => {
    expect(chromiumSetupFailureMessage(new Error("Executable does not exist"))).toContain(
      "bunx playwright install chromium"
    );
  });
});
