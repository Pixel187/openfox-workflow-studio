import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import AgentPalette from "../components/AgentPalette";
import { api, type AgentTemplate } from "../api";

const TEMPLATES: AgentTemplate[] = [
  {
    id: "planner",
    name: "Planner",
    description: "Planifie",
    collection: "general",
    type: "agent",
    phase: "planning",
    agentId: "builder",
    subGroup: "planning",
    prompt: "Planifie",
  },
  {
    id: "implementateur",
    name: "Implementateur",
    description: "Écrit le code",
    collection: "codage",
    type: "agent",
    phase: "build",
    agentId: "builder",
    subGroup: "build",
    prompt: "Implémente",
  },
  {
    id: "redacteur",
    name: "Rédacteur",
    description: "Rédige",
    collection: "redaction",
    type: "agent",
    phase: "build",
    agentId: "builder",
    subGroup: "build",
    prompt: "Rédige",
  },
];

describe("AgentPalette", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getAgentBase").mockResolvedValue(TEMPLATES);
  });

  it("affiche les gabarits groupés par collection", async () => {
    render(<AgentPalette />);
    await waitFor(() => expect(screen.getByText("Planner")).toBeInTheDocument());
    expect(screen.getByText("Général")).toBeInTheDocument();
    expect(screen.getByText("Codage")).toBeInTheDocument();
    expect(screen.getByText("Rédaction")).toBeInTheDocument();
    expect(screen.getByText("Implementateur")).toBeInTheDocument();
    expect(screen.getByText("Rédacteur")).toBeInTheDocument();
  });

  it("ouvre l'éditeur en mode création via + Nouvel agent", async () => {
    render(<AgentPalette />);
    await waitFor(() => expect(screen.getByText("Planner")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "+ Nouvel agent" }));
    expect(screen.getByText("Nouvel agent")).toBeInTheDocument();
    expect(screen.getByLabelText(/Identifiant/)).toBeInTheDocument();
  });

  it("ouvre l'éditeur en mode édition avec les valeurs du gabarit", async () => {
    render(<AgentPalette />);
    await waitFor(() => expect(screen.getByText("Planner")).toBeInTheDocument());
    const plannerCard = screen.getByText("Planner").closest("li")!;
    fireEvent.click(within(plannerCard).getByTitle("Modifier"));
    expect(screen.getByText("Modifier l'agent")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Planner")).toBeInTheDocument();
  });

  it("supprime un gabarit après confirmation", async () => {
    const deleteSpy = vi.spyOn(api, "deleteAgentTemplate").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<AgentPalette />);
    await waitFor(() => expect(screen.getByText("Planner")).toBeInTheDocument());
    const plannerCard = screen.getByText("Planner").closest("li")!;
    fireEvent.click(within(plannerCard).getByTitle("Supprimer"));
    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith("planner"));
  });

  it("n'appelle pas delete si l'utilisateur annule", async () => {
    const deleteSpy = vi.spyOn(api, "deleteAgentTemplate").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<AgentPalette />);
    await waitFor(() => expect(screen.getByText("Planner")).toBeInTheDocument());
    const plannerCard = screen.getByText("Planner").closest("li")!;
    fireEvent.click(within(plannerCard).getByTitle("Supprimer"));
    expect(deleteSpy).not.toHaveBeenCalled();
  });
});