import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import WorkflowList from "../components/WorkflowList";
import { api, type Workflow, type WorkflowSummary } from "../api";

const SUMMARY: WorkflowSummary[] = [
  { id: "demo", name: "Demo", description: "", version: "1.0.0", color: "#3b82f6", mtime: 1, stepCount: 2 },
];

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
        prompt: "Fais le travail",
        transitions: [{ goto: "$done" }],
      },
    ],
    startCondition: { type: "always" },
  };
}

describe("WorkflowList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "listWorkflows").mockResolvedValue(SUMMARY);
  });

  it("renomme un workflow via la modal", async () => {
    const wf = makeWorkflow();
    vi.spyOn(api, "getWorkflowWithEtag").mockResolvedValue({ workflow: wf, etag: '"abc"' });
    const updateSpy = vi.spyOn(api, "updateWorkflow").mockResolvedValue({
      ...wf,
      metadata: { ...wf.metadata, name: "Demo v2" },
    });

    render(<WorkflowList onOpen={() => {}} refreshKey={0} />);
    await waitFor(() => expect(screen.getByText("Demo")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Renommer"));
    const input = screen.getByDisplayValue("Demo");
    fireEvent.change(input, { target: { value: "Demo v2" } });
    const modal = screen.getByText("Renommer le workflow").closest("div")!;
    fireEvent.click(within(modal).getByRole("button", { name: "Renommer" }));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    expect(updateSpy).toHaveBeenCalledWith(
      "demo",
      expect.objectContaining({ metadata: expect.objectContaining({ name: "Demo v2" }) }),
      '"abc"',
    );
  });

  it("annule le renommage sans appeler updateWorkflow", async () => {
    const updateSpy = vi.spyOn(api, "updateWorkflow").mockResolvedValue(makeWorkflow());

    render(<WorkflowList onOpen={() => {}} refreshKey={0} />);
    await waitFor(() => expect(screen.getByText("Demo")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Renommer"));
    fireEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(updateSpy).not.toHaveBeenCalled();
  });
});