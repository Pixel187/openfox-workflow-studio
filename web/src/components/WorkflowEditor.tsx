import { useCallback } from "react";
import type { OnNodesChange } from "@xyflow/react";
import { useWorkflowStore } from "../store/workflowStore";
import { useDebouncedLayout } from "../hooks/useDebouncedLayout";
import WorkflowCanvas from "./WorkflowCanvas";
import StepInspector from "./StepInspector";
import ValidationPanel from "./ValidationPanel";
import AgentChat from "./AgentChat";
import AgentPalette from "./AgentPalette";
import { api } from "../api";
import { stepFromTemplate } from "../lib/stepFromTemplate";

interface WorkflowEditorProps {
  workflowId: string;
  onBack: () => void;
  onSaved: () => void;
}

export default function WorkflowEditor({ workflowId, onBack, onSaved }: WorkflowEditorProps) {
  const workflow = useWorkflowStore((s) => s.workflow);
  const selectedStepId = useWorkflowStore((s) => s.selectedStepId);
  const setSelectedStep = useWorkflowStore((s) => s.setSelectedStep);
  const save = useWorkflowStore((s) => s.save);
  const validate = useWorkflowStore((s) => s.validate);
  const dirty = useWorkflowStore((s) => s.dirty);
  const saving = useWorkflowStore((s) => s.saving);
  const error = useWorkflowStore((s) => s.error);
  const addStep = useWorkflowStore((s) => s.addStep);
  const connectSteps = useWorkflowStore((s) => s.connectSteps);
  const updateNodePositions = useWorkflowStore((s) => s.updateNodePositions);
  const scheduleLayout = useDebouncedLayout(workflow?.metadata.id ?? null);

  const onConnect = useCallback(
    (connection: { source: string | null; target: string | null }) => {
      if (!connection.source || !connection.target) return;
      connectSteps(connection.source, connection.target);
    },
    [connectSteps],
  );

  const onDropTemplate = useCallback(
    async (templateId: string, position: { x: number; y: number }) => {
      try {
        const templates = await api.getAgentBase();
        const template = templates.find((t) => t.id === templateId);
        if (!template) return;
        const step = stepFromTemplate(template);
        addStep(step);
        api
          .putLayout(workflow!.metadata.id, { nodes: [{ id: step.id, position }] })
          .catch(() => {});
      } catch {
        /* banque indisponible : on ignore le drop */
      }
    },
    [addStep, workflow],
  );

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      const positions = changes
        .filter((c): c is Extract<typeof c, { type: "position" }> => c.type === "position")
        .filter((c) => c.position)
        .map((c) => ({ id: c.id, position: c.position! }));
      if (positions.length > 0) {
        updateNodePositions(positions);
        scheduleLayout(positions);
      }
    },
    [updateNodePositions, scheduleLayout],
  );

  const exportJson = () => {
    const a = document.createElement("a");
    a.href = `/api/workflows/${workflowId}/export`;
    a.download = `${workflowId}.workflow.json`;
    a.click();
  };

  const exportZip = async () => {
    const response = await fetch("/api/export/bundle");
    if (!response.ok) {
      alert("Export ZIP impossible (backend indisponible)");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflows-bundle.zip";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!workflow) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        <p>Chargement…</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
        >
          ← Liste
        </button>
        <div className="flex-1">
          <span className="text-sm font-semibold text-slate-800">{workflow.metadata.name}</span>
          <span className="ml-2 text-xs text-slate-400">{workflow.metadata.id}</span>
          {dirty && <span className="ml-2 text-xs text-amber-600">● non sauvegardé</span>}
        </div>
        <button
          type="button"
          onClick={validate}
          className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
        >
          Valider
        </button>
        <button
          type="button"
          onClick={save}
          disabled={saving || !dirty}
          className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500 disabled:opacity-40"
        >
          {saving ? "Sauvegarde…" : "Sauvegarder"}
        </button>
        <button
          type="button"
          onClick={exportJson}
          className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
        >
          Export JSON
        </button>
        <button
          type="button"
          onClick={exportZip}
          className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
        >
          Export ZIP
        </button>
      </header>

      {error && (
        <div className="border-b border-red-200 bg-red-50 px-4 py-1 text-xs text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
          <AgentPalette />
        </aside>
        <div className="flex-1">
          <WorkflowCanvas
            workflow={workflow}
            selectedStepId={selectedStepId}
            onSelectStep={setSelectedStep}
            onNodesChange={onNodesChange}
            onDropTemplate={onDropTemplate}
            onConnect={onConnect}
          />
        </div>
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white">
          <StepInspector />
          <div className="border-t border-slate-200 p-3">
            <ValidationPanel />
          </div>
        </aside>
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white">
          <AgentChat onApplied={onSaved} />
        </aside>
      </div>
    </div>
  );
}