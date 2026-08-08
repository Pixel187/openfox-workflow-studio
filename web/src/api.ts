/**
 * Client API du Workflow Studio.
 *
 * Helpers fetch typés vers le backend FastAPI (proxy /api en dev).
 * Toutes les fonctions lèvent une Error lisible en cas d'échec HTTP.
 */

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  version: string;
  color: string;
  mtime: number;
  stepCount: number;
}

export interface Workflow {
  metadata: {
    id: string;
    name: string;
    description: string;
    version: string;
    color: string;
  };
  entryStep: string;
  settings: { maxIterations: number };
  steps: Step[];
  startCondition: { type: string };
}

export interface Step {
  id: string;
  name: string;
  type: string;
  phase: string;
  agentId: string;
  subAgentType?: string;
  subGroup?: string;
  prompt: string;
  nudgePrompt?: string;
  transitions: { when?: string; goto: string }[];
  /** Position canvas (sidecar layout), ignorée par OpenFox. */
  position?: { x: number; y: number };
}

export interface VariableCategory {
  name: string;
  items: { name: string; description: string; example?: string }[];
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  collection: string;
  type: string;
  phase: string;
  agentId: string;
  subAgentType?: string;
  subGroup: string;
  prompt: string;
  nudgePrompt?: string;
}

export interface AgentTemplatePayload {
  id: string;
  name: string;
  description: string;
  collection: string;
  type: string;
  phase: string;
  agentId: string;
  subAgentType?: string;
  subGroup: string;
  prompt: string;
  nudgePrompt?: string;
}

export interface ValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ProposalResponse {
  proposal_id: string;
  proposed: Workflow;
  diff: { added: string[]; removed: string[]; modified: string[] };
  validation: ValidationReport;
  preserves_vars: boolean;
  lost_vars: string[];
}

async function request<T>(path: string, method: string = "GET", body?: unknown): Promise<T> {
  const options: RequestInit = {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* corps non JSON */
    }
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  listWorkflows: () => request<WorkflowSummary[]>("/api/workflows"),
  getWorkflow: (id: string) => request<Workflow>(`/api/workflows/${id}`),
  getWorkflowWithEtag: async (id: string): Promise<{ workflow: Workflow; etag: string }> => {
    const response = await fetch(`/api/workflows/${id}`);
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = await response.json();
        if (typeof data.detail === "string") detail = data.detail;
      } catch {
        /* ignore */
      }
      throw new Error(`HTTP ${response.status}: ${detail}`);
    }
    const workflow = (await response.json()) as Workflow;
    return { workflow, etag: response.headers.get("ETag") ?? "" };
  },
  createWorkflow: (wf: Workflow) => request<Workflow>("/api/workflows", "POST", wf),
  updateWorkflow: (id: string, wf: Workflow, etag: string) =>
    requestWithHeaders<Workflow>("PUT", `/api/workflows/${id}`, wf, { "If-Match": etag }),
  deleteWorkflow: (id: string, etag: string) =>
    requestWithHeaders<void>("DELETE", `/api/workflows/${id}`, undefined, { "If-Match": etag }),
  validateWorkflow: (id: string) => request<ValidationReport>(`/api/workflows/${id}/validate`, "POST"),
  getLayout: (id: string) => request<Record<string, unknown>>(`/api/workflows/${id}/layout`),
  putLayout: (id: string, layout: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/workflows/${id}/layout`, "PUT", layout),
  getVariables: () => request<VariableCategory[]>("/api/variables"),
  getAgentBase: () => request<AgentTemplate[]>("/api/agent-base"),
  getAgentTemplate: (id: string) => request<AgentTemplate>(`/api/agent-base/${id}`),
  createAgentTemplate: (payload: AgentTemplatePayload) =>
    request<AgentTemplate>("/api/agent-base", "POST", payload),
  updateAgentTemplate: (id: string, payload: AgentTemplatePayload) =>
    request<AgentTemplate>(`/api/agent-base/${id}`, "PUT", payload),
  deleteAgentTemplate: (id: string) => request<void>(`/api/agent-base/${id}`, "DELETE"),
  getModels: () => request<{ models: string[] }>("/api/ollama/models"),
  propose: (payload: {
    workflow_id: string;
    scope: string;
    step_id?: string;
    instruction: string;
    model?: string;
  }) => request<ProposalResponse>("/api/agent/propose", "POST", payload),
  apply: (proposal_id: string) =>
    request<{ workflow: Workflow; etag: string }>("/api/agent/apply", "POST", { proposal_id }),
  discard: (proposal_id: string) => request<void>("/api/agent/discard", "POST", { proposal_id }),
};

/** Requête avec en-têtes personnalisés (If-Match pour l'optimistic locking). */
async function requestWithHeaders<T>(
  method: string,
  path: string,
  body: unknown,
  headers: Record<string, string>
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { requestWithHeaders };