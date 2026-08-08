import { describe, expect, it } from "vitest";
import { stepFromTemplate } from "../lib/stepFromTemplate";
import type { AgentTemplate } from "../api";

const planner: AgentTemplate = {
  id: "planner",
  name: "Planner",
  description: "Planifie le travail",
  collection: "general",
  type: "agent",
  phase: "planning",
  agentId: "builder",
  subGroup: "planning",
  prompt: "Planifie avec {{workdir}}",
  nudgePrompt: "Sois précis",
};

describe("stepFromTemplate", () => {
  it("génère un step avec id agent-<slug>-<ts> et champs copiés", () => {
    const step = stepFromTemplate(planner, 1234567890);
    expect(step.id).toBe("agent-planner-1234567890");
    expect(step.name).toBe("Planner");
    expect(step.type).toBe("agent");
    expect(step.phase).toBe("planning");
    expect(step.agentId).toBe("builder");
    expect(step.subGroup).toBe("planning");
    expect(step.prompt).toBe("Planifie avec {{workdir}}");
    expect(step.nudgePrompt).toBe("Sois précis");
  });

  it("copie subAgentType quand présent", () => {
    const verifier: AgentTemplate = {
      ...planner,
      id: "verifier",
      name: "Verifier",
      type: "sub_agent",
      subAgentType: "verifier",
      phase: "verification",
    };
    const step = stepFromTemplate(verifier, 1);
    expect(step.subAgentType).toBe("verifier");
    expect(step.type).toBe("sub_agent");
  });

  it("transition par défaut vers $done", () => {
    const step = stepFromTemplate(planner, 1);
    expect(step.transitions).toEqual([{ goto: "$done" }]);
  });

  it("slugifie le nom (accents, espaces, casse)", () => {
    const t: AgentTemplate = { ...planner, name: "Builder-Drafter Étape" };
    const step = stepFromTemplate(t, 42);
    expect(step.id).toBe("agent-builder-drafter-tape-42");
  });
});