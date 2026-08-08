import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AgentChat from "../components/AgentChat";
import { api, type Workflow } from "../api";
import { useWorkflowStore } from "../store/workflowStore";

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
    ],
    startCondition: { type: "always" },
  };
}

describe("AgentChat", () => {
  beforeEach(() => {
    useWorkflowStore.setState({ workflow: makeWorkflow(), selectedStepId: "s1" });
    vi.restoreAllMocks();
  });

  it("affiche le diff après une proposition", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
    vi.spyOn(api, "propose").mockResolvedValue({
      proposal_id: "p1",
      proposed: makeWorkflow(),
      diff: { added: ["s2"], removed: [], modified: [] },
      validation: { valid: true, errors: [], warnings: [] },
      preserves_vars: true,
      lost_vars: [],
    });
    render(<AgentChat onApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "Ajoute une étape" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() => expect(screen.getByText("+ s2")).toBeInTheDocument());
    expect(screen.getByText("variables préservées")).toBeInTheDocument();
  });

  it("Approuver appelle apply puis onApplied", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
    vi.spyOn(api, "propose").mockResolvedValue({
      proposal_id: "p1",
      proposed: makeWorkflow(),
      diff: { added: [], removed: [], modified: ["s1"] },
      validation: { valid: true, errors: [], warnings: [] },
      preserves_vars: true,
      lost_vars: [],
    });
    const applySpy = vi.spyOn(api, "apply").mockResolvedValue({ workflow: makeWorkflow(), etag: '"x"' });
    const onApplied = vi.fn();
    render(<AgentChat onApplied={onApplied} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "Améliore" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Approuver" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Approuver" }));
    await waitFor(() => expect(applySpy).toHaveBeenCalledWith("p1"));
    expect(onApplied).toHaveBeenCalled();
  });

  it("affiche une erreur lisible quand Ollama est down", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: [] });
    vi.spyOn(api, "propose").mockRejectedValue(new Error("HTTP 502: Ollama indisponible"));
    render(<AgentChat onApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() => expect(screen.getByText(/Ollama indisponible/)).toBeInTheDocument());
  });
});