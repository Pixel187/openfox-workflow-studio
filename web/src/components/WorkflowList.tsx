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
  const [renaming, setRenaming] = useState<WorkflowSummary | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renamingBusy, setRenamingBusy] = useState(false);

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

  const startRename = (wf: WorkflowSummary) => {
    setRenameDraft(wf.name);
    setRenaming(wf);
  };

  const commitRename = async () => {
    if (!renaming) return;
    const name = renameDraft.trim();
    if (!name || name === renaming.name) {
      setRenaming(null);
      return;
    }
    setRenamingBusy(true);
    setError("");
    try {
      const detail = await api.getWorkflowWithEtag(renaming.id);
      const updated = { ...detail.workflow, metadata: { ...detail.workflow.metadata, name } };
      await api.updateWorkflow(renaming.id, updated, detail.etag);
      setRenaming(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRenamingBusy(false);
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
                onClick={() => startRename(wf)}
                title="Renommer"
                className="ml-2 rounded bg-slate-700 px-2 py-1 text-[10px] text-slate-300 opacity-0 hover:bg-blue-700 hover:text-white group-hover:opacity-100"
              >
                Renommer
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
      {renaming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-80 rounded bg-slate-800 p-4 shadow-lg">
            <h2 className="mb-2 text-sm font-semibold text-slate-100">Renommer le workflow</h2>
            <input
              autoFocus
              value={renameDraft}
              onChange={(e) => setRenameDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") setRenaming(null);
              }}
              className="w-full rounded border border-slate-600 bg-slate-900 px-2 py-1 text-sm text-slate-100"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRenaming(null)}
                disabled={renamingBusy}
                className="rounded bg-slate-700 px-3 py-1 text-xs text-slate-200 hover:bg-slate-600 disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={commitRename}
                disabled={renamingBusy || !renameDraft.trim()}
                className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {renamingBusy ? "Renommage…" : "Renommer"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}