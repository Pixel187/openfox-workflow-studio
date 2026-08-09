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
      diff: { added: [{ id: "s2", name: "Étape 2" }], removed: [], modified: [] },
      validation: { valid: true, errors: [], warnings: [] },
      preserves_vars: true,
      lost_vars: [],
    });
    render(<AgentChat onApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "Ajoute une étape" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() => expect(screen.getByText("+ Étape 2 (s2)")).toBeInTheDocument());
    expect(screen.getByText("variables préservées")).toBeInTheDocument();
  });

  it("affiche les changements de champs pour une étape modifiée", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
    vi.spyOn(api, "propose").mockResolvedValue({
      proposal_id: "p1",
      proposed: makeWorkflow(),
      diff: {
        added: [],
        removed: [],
        modified: [
          {
            id: "s1",
            name: "Build",
            changes: [
              { field: "prompt", before: "Utilise {{workdir}}", after: "Utilise {{workdir}} et vérifie" },
            ],
          },
        ],
      },
      validation: { valid: true, errors: [], warnings: [] },
      preserves_vars: true,
      lost_vars: [],
    });
    render(<AgentChat onApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "Améliore" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() => expect(screen.getByText("~ Build (s1)")).toBeInTheDocument());
    expect(screen.getByText("prompt")).toBeInTheDocument();
    expect(screen.getByText("Utilise {{workdir}} et vérifie")).toBeInTheDocument();
  });

  it("affiche la bannière fallback quand le modèle par défaut a été utilisé", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
    vi.spyOn(api, "propose").mockResolvedValue({
      proposal_id: "p1",
      proposed: makeWorkflow(),
      diff: { added: [], removed: [], modified: [{ id: "s1", name: "Build" }] },
      validation: { valid: true, errors: [], warnings: [] },
      preserves_vars: true,
      lost_vars: [],
      fallback_used: true,
      fallback_model: "mistral-small3.2",
    });
    render(<AgentChat onApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Ex : ajoute une étape de vérification"), {
      target: { value: "Ajoute" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Proposer" }));
    await waitFor(() =>
      expect(screen.getByText(/généré avec mistral-small3.2/)).toBeInTheDocument(),
    );
  });

  it("Approuver appelle apply puis onApplied", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
    vi.spyOn(api, "propose").mockResolvedValue({
      proposal_id: "p1",
      proposed: makeWorkflow(),
      diff: { added: [], removed: [], modified: [{ id: "s1", name: "Build" }] },
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

  it("sélectionne le modèle par défaut du backend quand il est disponible", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({
      models: ["rafw007/Qwen3.6-35B:latest", "mistral-small3.2:latest", "qwen2.5:32b"],
      default_model: "mistral-small3.2",
    });
    render(<AgentChat onApplied={() => {}} />);
    await waitFor(() =>
      expect(screen.getByLabelText(/Modèle/)).toHaveValue("mistral-small3.2:latest"),
    );
  });

  it("replie sur le premier modèle si le défaut est absent", async () => {
    vi.spyOn(api, "getModels").mockResolvedValue({
      models: ["qwen2.5:32b", "gemma4:12b"],
      default_model: "mistral-small3.2",
    });
    render(<AgentChat onApplied={() => {}} />);
    await waitFor(() => expect(screen.getByLabelText(/Modèle/)).toHaveValue("qwen2.5:32b"));
  });
});