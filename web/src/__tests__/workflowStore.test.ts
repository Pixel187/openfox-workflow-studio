import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkflowStore } from "../store/workflowStore";
import { api, type Workflow } from "../api";

function makeWorkflow(): Workflow {
  return {
    metadata: { id: "demo", name: "Demo", description: "", version: "1.0.0", color: "#3b82f6" },
    entryStep: "s1",
    settings: { maxIterations: 50 },
    steps: [
      {
        id: "s1",
        name: "Build",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "Utilise {{workdir}}",
        transitions: [{ goto: "$done" }],
      },
      {
        id: "s2",
        name: "Verify",
        type: "sub_agent",
        phase: "verification",
        agentId: "builder",
        subAgentType: "verifier",
        prompt: "Vérifie",
        transitions: [{ goto: "$done" }],
      },
    ],
    startCondition: { type: "always" },
  };
}

describe("workflowStore", () => {
  beforeEach(() => {
    useWorkflowStore.getState().reset();
    vi.restoreAllMocks();
  });

  it("loadWorkflow charge le workflow et l'etag", async () => {
    vi.spyOn(api, "getWorkflowWithEtag").mockResolvedValue({
      workflow: makeWorkflow(),
      etag: '"abc"',
    });
    await useWorkflowStore.getState().loadWorkflow("demo");
    const state = useWorkflowStore.getState();
    expect(state.workflow?.metadata.id).toBe("demo");
    expect(state.etag).toBe('"abc"');
    expect(state.dirty).toBe(false);
  });

  it("updateStep modifie l'étape et marque dirty", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().updateStep("s1", { name: "Build v2" });
    const state = useWorkflowStore.getState();
    expect(state.workflow?.steps[0].name).toBe("Build v2");
    expect(state.dirty).toBe(true);
  });

  it("addStep ajoute une étape et la sélectionne", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().addStep({
      id: "s3",
      name: "Review",
      type: "agent",
      phase: "review",
      agentId: "builder",
      prompt: "Relis",
      transitions: [{ goto: "$done" }],
    });
    const state = useWorkflowStore.getState();
    expect(state.workflow?.steps).toHaveLength(3);
    expect(state.selectedStepId).toBe("s3");
  });

  it("removeStep bloque la suppression de entryStep", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().removeStep("s1");
    expect(useWorkflowStore.getState().workflow?.steps).toHaveLength(2);
  });

  it("removeStep supprime une étape non-entry et ses transitions", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().removeStep("s2");
    const steps = useWorkflowStore.getState().workflow?.steps;
    expect(steps).toHaveLength(1);
    expect(steps![0].transitions).toHaveLength(1);
  });

  it("duplicateStep crée une copie avec id unique", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().duplicateStep("s1");
    const steps = useWorkflowStore.getState().workflow?.steps;
    expect(steps).toHaveLength(3);
    expect(steps![2].id).toMatch(/^s1-copy-/);
    expect(steps![2].name).toContain("(copie)");
  });

  it("connectSteps ajoute une transition {goto} et marque dirty", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().connectSteps("s1", "s2");
    const s1 = useWorkflowStore.getState().workflow?.steps[0];
    expect(s1?.transitions).toContainEqual({ goto: "s2" });
    expect(useWorkflowStore.getState().dirty).toBe(true);
  });

  it("connectSteps ignore les doublons et l'auto-connexion", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().connectSteps("s1", "$done");
    useWorkflowStore.getState().connectSteps("s1", "$done");
    useWorkflowStore.getState().connectSteps("s1", "s1");
    const s1 = useWorkflowStore.getState().workflow?.steps[0];
    expect(s1?.transitions).toHaveLength(1);
  });

  it("moveStep déplace une étape vers le haut", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().moveStep("s2", "up");
    const ids = useWorkflowStore.getState().workflow?.steps.map((s) => s.id);
    expect(ids).toEqual(["s2", "s1"]);
    expect(useWorkflowStore.getState().dirty).toBe(true);
  });

  it("moveStep ignore le déplacement hors bornes", () => {
    useWorkflowStore.setState({ workflow: makeWorkflow() });
    useWorkflowStore.getState().moveStep("s1", "up");
    useWorkflowStore.getState().moveStep("s2", "down");
    const ids = useWorkflowStore.getState().workflow?.steps.map((s) => s.id);
    expect(ids).toEqual(["s1", "s2"]);
  });

  it("save appelle updateWorkflow avec l'etag", async () => {
    const wf = makeWorkflow();
    useWorkflowStore.setState({ workflow: wf, etag: '"abc"' });
    const spy = vi.spyOn(api, "updateWorkflow").mockResolvedValue(wf);
    await useWorkflowStore.getState().save();
    expect(spy).toHaveBeenCalledWith("demo", wf, '"abc"');
    expect(useWorkflowStore.getState().dirty).toBe(false);
  });

  it("save capture l'erreur HTTP et garde dirty", async () => {
    const wf = makeWorkflow();
    useWorkflowStore.setState({ workflow: wf, etag: '"abc"', dirty: true });
    vi.spyOn(api, "updateWorkflow").mockRejectedValue(new Error("HTTP 409: ETag périmé"));
    await useWorkflowStore.getState().save();
    expect(useWorkflowStore.getState().error).toContain("409");
    expect(useWorkflowStore.getState().dirty).toBe(true);
  });
});