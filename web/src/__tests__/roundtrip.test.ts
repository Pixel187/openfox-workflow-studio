import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { serializeWorkflow, deserializeWorkflow } from "../lib/serialize";
import type { Workflow } from "../api";

const REAL_WORKFLOW = join(
  homedir(),
  "AppData",
  "Roaming",
  "openfox",
  "workflows",
  "build-and-verify.workflow.json",
);

function loadRealWorkflow(): Workflow {
  return JSON.parse(readFileSync(REAL_WORKFLOW, "utf-8")) as Workflow;
}

describe("round-trip serialize/deserialize", () => {
  it("conserve tous les steps, transitions et variables (modulo positions)", () => {
    const wf = loadRealWorkflow();
    const { nodes } = serializeWorkflow(wf);
    const restored = deserializeWorkflow(wf, nodes);

    expect(restored.steps).toHaveLength(wf.steps.length);
    expect(restored.steps.map((s) => s.id)).toEqual(wf.steps.map((s) => s.id));

    // Transitions conservées
    for (const step of wf.steps) {
      const restoredStep = restored.steps.find((s) => s.id === step.id)!;
      expect(restoredStep.transitions).toEqual(step.transitions);
    }

    // Variables {{...}} conservées dans les prompts
    const varRegex = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
    const originalVars = new Set(
      wf.steps.flatMap((s) => [...(s.prompt.matchAll(varRegex))].map((m) => m[1])),
    );
    const restoredVars = new Set(
      restored.steps.flatMap((s) => [...(s.prompt.matchAll(varRegex))].map((m) => m[1])),
    );
    expect(restoredVars).toEqual(originalVars);
  });

  it("produit un noeud par step + noeud terminal", () => {
    const wf = loadRealWorkflow();
    const { nodes, edges } = serializeWorkflow(wf);
    expect(nodes).toHaveLength(wf.steps.length + 1); // + $done
    expect(nodes.some((n) => n.id === "$done")).toBe(true);
    expect(edges).toHaveLength(wf.steps.length); // une transition par step
  });
});