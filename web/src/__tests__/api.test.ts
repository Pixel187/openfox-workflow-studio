import { describe, expect, it, vi, beforeEach } from "vitest";
import { api } from "../api";

describe("api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("listWorkflows GET /api/workflows et parse la liste", async () => {
    const fake = [{ id: "demo", name: "Demo", stepCount: 1 }];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => fake,
      })
    );
    const result = await api.listWorkflows();
    expect(result).toEqual(fake);
    expect(fetch).toHaveBeenCalledWith("/api/workflows", expect.any(Object));
  });

  it("updateWorkflow envoie If-Match", async () => {
    const wf = { metadata: { id: "demo" } };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => wf,
      }),
    );
    await api.updateWorkflow("demo", wf as never, '"abc"');
    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.headers["If-Match"]).toBe('"abc"');
  });

  it("lève une Error lisible sur HTTP 409", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        statusText: "Conflict",
        json: async () => ({ detail: "ETag périmé" }),
      }),
    );
    await expect(api.updateWorkflow("demo", {} as never, '"x"')).rejects.toThrow(
      "ETag périmé",
    );
  });

  it("propose POST /api/agent/propose avec le payload", async () => {
    const proposal = { proposal_id: "p1", proposed: {}, diff: { added: [], removed: [], modified: [] } };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => proposal,
      }),
    );
    const result = await api.propose({
      workflow_id: "demo",
      scope: "workflow",
      instruction: "Ajoute une étape",
    });
    expect(result.proposal_id).toBe("p1");
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/agent/propose");
    expect(JSON.parse(options.body).instruction).toBe("Ajoute une étape");
  });

  it("createAgentTemplate POST /api/agent-base avec le payload", async () => {
    const template = {
      id: "nouveau",
      name: "Nouveau",
      collection: "codage",
      type: "agent",
      phase: "build",
      agentId: "builder",
      subGroup: "build",
      prompt: "Fais le travail",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => template,
      }),
    );
    const result = await api.createAgentTemplate(template as never);
    expect(result.id).toBe("nouveau");
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/agent-base");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body).collection).toBe("codage");
  });

  it("updateAgentTemplate PUT /api/agent-base/{id}", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: "planner", name: "Planner v2" }),
      }),
    );
    await api.updateAgentTemplate("planner", { id: "planner", name: "Planner v2" } as never);
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/agent-base/planner");
    expect(options.method).toBe("PUT");
  });

  it("deleteAgentTemplate DELETE /api/agent-base/{id}", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 204 }),
    );
    await api.deleteAgentTemplate("planner");
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/agent-base/planner");
    expect(options.method).toBe("DELETE");
  });

  it("lève une Error lisible sur createAgentTemplate 409", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        statusText: "Conflict",
        json: async () => ({ detail: "Gabarit 'planner' existe déjà" }),
      }),
    );
    await expect(
      api.createAgentTemplate({ id: "planner" } as never),
    ).rejects.toThrow("existe déjà");
  });
});