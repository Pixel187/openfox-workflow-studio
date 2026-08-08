import { describe, expect, it } from "vitest";
import { serializeWorkflow, phaseColor, deserializeWorkflow } from "../lib/serialize";
import type { Workflow } from "../api";

function makeWorkflow(steps: Workflow["steps"]): Workflow {
  return {
    metadata: { id: "demo", name: "Demo", description: "", version: "1.0.0", color: "#3b82f6" },
    entryStep: steps[0]?.id ?? "",
    settings: { maxIterations: 50 },
    steps,
    startCondition: { type: "always" },
  };
}

describe("serializeWorkflow", () => {
  it("convertit un workflow en noeuds par phase", () => {
    const wf = makeWorkflow([
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "x",
        transitions: [{ goto: "s2" }],
      },
      {
        id: "s2",
        name: "Verify",
        type: "sub_agent",
        phase: "verification",
        agentId: "builder",
        subAgentType: "verifier",
        prompt: "y",
        transitions: [{ goto: "$done" }],
      },
    ]);
    const { nodes, edges } = serializeWorkflow(wf);
    expect(nodes).toHaveLength(3); // s1, s2, $done
    expect(edges).toHaveLength(2);
    const s1 = nodes.find((n) => n.id === "s1")!;
    const s2 = nodes.find((n) => n.id === "s2")!;
    expect(s1.position.x).toBeLessThan(s2.position.x); // build avant verification
    expect(s2.data.subAgentType).toBe("verifier");
  });

  it("reconnaît une boucle build->build", () => {
    const wf = makeWorkflow([
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "x",
        transitions: [{ goto: "s1" }],
      },
    ]);
    const { edges } = serializeWorkflow(wf);
    expect(edges[0].animated).toBe(true);
    expect(edges[0].label).toBe("loop");
  });

  it("ne marque pas une transition forward comme boucle", () => {
    const wf = makeWorkflow([
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "x",
        transitions: [{ goto: "s2" }],
      },
      {
        id: "s2",
        name: "Verify",
        type: "agent",
        phase: "verification",
        agentId: "builder",
        prompt: "y",
        transitions: [{ goto: "$done" }],
      },
    ]);
    const { edges } = serializeWorkflow(wf);
    expect(edges[0].animated).toBeFalsy();
  });

  it("workflow vide -> aucun noeud, pas d'erreur", () => {
    const { nodes, edges } = serializeWorkflow(makeWorkflow([]));
    expect(nodes).toHaveLength(0);
    expect(edges).toHaveLength(0);
  });

  it("utilise step.position quand elle est présente", () => {
    const wf = makeWorkflow([
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "x",
        position: { x: 999, y: 777 },
        transitions: [{ goto: "$done" }],
      },
    ]);
    const { nodes } = serializeWorkflow(wf);
    const s1 = nodes.find((n) => n.id === "s1")!;
    expect(s1.position).toEqual({ x: 999, y: 777 });
  });
});

describe("phaseColor", () => {
  it("retourne une couleur par phase connue", () => {
    expect(phaseColor("build")).toBe("#3b82f6");
    expect(phaseColor("verification")).toBe("#8b5cf6");
  });
  it("retourne un gris pour une phase inconnue", () => {
    expect(phaseColor("inconnue")).toBe("#64748b");
  });
});

describe("deserializeWorkflow", () => {
  it("réinjecte les positions dans les steps", () => {
    const wf = makeWorkflow([
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "x",
        transitions: [{ goto: "$done" }],
      },
    ]);
    const nodes = [{ id: "s1", position: { x: 10, y: 20 }, data: { label: "Build", phase: "build", type: "agent" } }];
    const out = deserializeWorkflow(wf, nodes);
    expect(out.steps[0]).toMatchObject({ id: "s1", position: { x: 10, y: 20 } });
  });
});