import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AgentEditor from "../components/AgentEditor";
import { api, type AgentTemplate } from "../api";

const TEMPLATE: AgentTemplate = {
  id: "planner",
  name: "Planner",
  description: "Planifie",
  collection: "general",
  type: "agent",
  phase: "planning",
  agentId: "builder",
  subGroup: "planning",
  prompt: "Planifie",
};

describe("AgentEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getModels").mockResolvedValue({ models: ["mistral-small3.2"] });
  });

  it("crée un agent via POST avec le payload rempli", async () => {
    const createSpy = vi.spyOn(api, "createAgentTemplate").mockResolvedValue(TEMPLATE);
    const onSaved = vi.fn();
    render(<AgentEditor template={null} onClose={() => {}} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText(/Identifiant/), { target: { value: "mon-agent" } });
    fireEvent.change(screen.getByLabelText(/Nom/), { target: { value: "Mon Agent" } });
    fireEvent.change(screen.getByLabelText(/Prompt/), { target: { value: "Fais le travail" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer" }));
    await waitFor(() => expect(createSpy).toHaveBeenCalled());
    expect(createSpy.mock.calls[0][0].id).toBe("mon-agent");
    expect(onSaved).toHaveBeenCalled();
  });

  it("bloque la création si l'id est invalide (majuscules)", async () => {
    const createSpy = vi.spyOn(api, "createAgentTemplate").mockResolvedValue(TEMPLATE);
    render(<AgentEditor template={null} onClose={() => {}} onSaved={() => {}} />);
    fireEvent.change(screen.getByLabelText(/Identifiant/), { target: { value: "Mon Agent" } });
    fireEvent.change(screen.getByLabelText(/Nom/), { target: { value: "Mon Agent" } });
    fireEvent.change(screen.getByLabelText(/Prompt/), { target: { value: "Vais" } });
    expect(screen.getByText(/minuscules/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Créer" }));
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("pré-remplit le formulaire en mode édition et appelle PUT", async () => {
    const updateSpy = vi.spyOn(api, "updateAgentTemplate").mockResolvedValue(TEMPLATE);
    const onSaved = vi.fn();
    render(<AgentEditor template={TEMPLATE} onClose={() => {}} onSaved={onSaved} />);
    expect(screen.getByDisplayValue("planner")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Planner")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Nom/), { target: { value: "Planner v2" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(updateSpy).toHaveBeenCalledWith("planner", expect.objectContaining({ name: "Planner v2" })));
    expect(onSaved).toHaveBeenCalled();
  });

  it("affiche l'erreur HTTP du backend", async () => {
    vi.spyOn(api, "createAgentTemplate").mockRejectedValue(new Error("HTTP 409: Gabarit 'planner' existe déjà"));
    render(<AgentEditor template={null} onClose={() => {}} onSaved={() => {}} />);
    fireEvent.change(screen.getByLabelText(/Identifiant/), { target: { value: "planner" } });
    fireEvent.change(screen.getByLabelText(/Nom/), { target: { value: "Doublon" } });
    fireEvent.change(screen.getByLabelText(/Prompt/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer" }));
    await waitFor(() => expect(screen.getByText(/existe déjà/)).toBeInTheDocument());
  });

  it("Générer avec l'IA pré-remplit le formulaire", async () => {
    const generated: AgentTemplate = {
      id: "auditeur-rgpd",
      name: "Auditeur RGPD",
      description: "Vérifie la conformité RGPD d'un dossier.",
      collection: "juridique",
      type: "sub_agent",
      phase: "verification",
      agentId: "builder",
      subAgentType: "verifier",
      subGroup: "verify",
      prompt: "Vérifie la conformité RGPD. step_done()",
      nudgePrompt: "Cite les sources officielles.",
    };
    const generateSpy = vi.spyOn(api, "generateAgentTemplate").mockResolvedValue(generated);
    render(<AgentEditor template={null} onClose={() => {}} onSaved={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/Décris l'agent/), {
      target: { value: "Audit RGPD" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Générer avec l'IA" }));
    await waitFor(() => expect(generateSpy).toHaveBeenCalledWith(expect.objectContaining({ description: "Audit RGPD" })));
    expect(screen.getByDisplayValue("auditeur-rgpd")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Auditeur RGPD")).toBeInTheDocument();
    expect(screen.getByLabelText(/Prompt/)).toHaveValue("Vérifie la conformité RGPD. step_done()");
  });

  it("affiche l'erreur de génération IA", async () => {
    vi.spyOn(api, "generateAgentTemplate").mockRejectedValue(new Error("HTTP 502: Ollama down"));
    render(<AgentEditor template={null} onClose={() => {}} onSaved={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/Décris l'agent/), {
      target: { value: "Audit RGPD" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Générer avec l'IA" }));
    await waitFor(() => expect(screen.getByText(/Ollama down/)).toBeInTheDocument());
  });
});