import { useEffect, useState } from "react";
import { api, type WorkflowSummary } from "../api";

interface WorkflowListProps {
  onOpen: (id: string) => void;
  refreshKey: number;
}

export default function WorkflowList({ onOpen, refreshKey }: WorkflowListProps) {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () => {
    api
      .listWorkflows()
      .then(setWorkflows)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(load, [refreshKey]);

  const create = async () => {
    setCreating(true);
    setError("");
    try {
      const wf = await api.createWorkflow({
        metadata: {
          id: "",
          name: "Nouveau workflow",
          description: "",
          version: "1.0.0",
          color: "#3b82f6",
        },
        entryStep: "s1",
        settings: { maxIterations: 50 },
        steps: [
          {
            id: "s1",
            name: "Étape 1",
            type: "agent",
            phase: "build",
            agentId: "builder",
            prompt: "Fais le travail",
            transitions: [{ goto: "$done" }],
          },
        ],
        startCondition: { type: "always" },
      });
      onOpen(wf.metadata.id);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const remove = async (wf: WorkflowSummary) => {
    if (!window.confirm(`Supprimer « ${wf.name} » ?`)) return;
    try {
      const detail = await api.getWorkflowWithEtag(wf.id);
      await api.deleteWorkflow(wf.id, detail.etag);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h1 className="text-sm font-semibold tracking-wide text-slate-100">
          OpenFox Workflow Studio
        </h1>
        <button
          type="button"
          onClick={create}
          disabled={creating}
          className="rounded bg-blue-600 px-2 py-1 text-[10px] text-white hover:bg-blue-500 disabled:opacity-50"
        >
          + Nouveau
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {error && <p className="mb-2 text-xs text-red-400">{error}</p>}
        <ul className="space-y-1">
          {workflows.map((wf) => (
            <li
              key={wf.id}
              className="group flex items-center justify-between rounded bg-slate-800 px-3 py-2 hover:bg-slate-700"
            >
              <button
                type="button"
                onClick={() => onOpen(wf.id)}
                className="flex-1 text-left"
              >
                <div className="text-sm font-medium text-slate-100">{wf.name}</div>
                <div className="text-xs text-slate-400">
                  {wf.id} · {wf.stepCount} étapes
                </div>
              </button>
              <button
                type="button"
                onClick={() => remove(wf)}
                className="ml-2 rounded bg-slate-700 px-2 py-1 text-[10px] text-slate-300 opacity-0 hover:bg-red-700 hover:text-white group-hover:opacity-100"
              >
                Suppr.
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}