import { useWorkflowStore } from "../store/workflowStore";
import PromptField from "./PromptField";
import type { Step } from "../api";

const PHASES = ["build", "generate", "verification", "review"];
const TYPES = ["agent", "sub_agent"];

export default function StepInspector() {
  const workflow = useWorkflowStore((s) => s.workflow);
  const selectedStepId = useWorkflowStore((s) => s.selectedStepId);
  const updateStep = useWorkflowStore((s) => s.updateStep);
  const removeStep = useWorkflowStore((s) => s.removeStep);
  const duplicateStep = useWorkflowStore((s) => s.duplicateStep);
  const moveStep = useWorkflowStore((s) => s.moveStep);

  if (!workflow) return null;
  const step = workflow.steps.find((s) => s.id === selectedStepId);
  if (!step) {
    return (
      <div className="p-4 text-xs text-slate-400">
        Sélectionnez une étape sur le canvas pour l'inspecter.
      </div>
    );
  }

  const set = (patch: Partial<Step>) => updateStep(step.id, patch);
  const isEntry = workflow.entryStep === step.id;
  const stepIds = workflow.steps.map((s) => s.id);
  const stepIndex = workflow.steps.findIndex((s) => s.id === step.id);
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === workflow.steps.length - 1;

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Étape
        </h2>
        <div className="flex gap-1">
          <button
            type="button"
            disabled={isFirst}
            onClick={() => moveStep(step.id, "up")}
            className="rounded bg-slate-200 px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-300 disabled:opacity-40"
            title="Monter dans l'ordre"
          >
            ↑
          </button>
          <button
            type="button"
            disabled={isLast}
            onClick={() => moveStep(step.id, "down")}
            className="rounded bg-slate-200 px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-300 disabled:opacity-40"
            title="Descendre dans l'ordre"
          >
            ↓
          </button>
          <button
            type="button"
            onClick={() => duplicateStep(step.id)}
            className="rounded bg-slate-700 px-2 py-1 text-[10px] text-slate-200 hover:bg-slate-600"
          >
            Dupliquer
          </button>
          <button
            type="button"
            disabled={isEntry}
            onClick={() => removeStep(step.id)}
            className="rounded bg-red-700 px-2 py-1 text-[10px] text-white hover:bg-red-600 disabled:opacity-40"
            title={isEntry ? "Impossible de supprimer l'étape d'entrée" : "Supprimer"}
          >
            Supprimer
          </button>
        </div>
      </div>
      {isEntry && (
        <p className="text-[10px] text-amber-500">
          Étape d'entrée : la suppression est bloquée.
        </p>
      )}

      <label className="block">
        <span className="text-[10px] text-slate-500">ID (lecture seule)</span>
        <input
          value={step.id}
          readOnly
          className="mt-1 w-full rounded border border-slate-300 bg-slate-100 px-2 py-1 text-xs text-slate-500"
        />
      </label>

      <label className="block">
        <span className="text-[10px] text-slate-500">Nom</span>
        <input
          value={step.name}
          onChange={(e) => set({ name: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
      </label>

      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className="text-[10px] text-slate-500">Type</span>
          <select
            value={step.type}
            onChange={(e) => set({ type: e.target.value })}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-[10px] text-slate-500">Phase</span>
          <select
            value={step.phase}
            onChange={(e) => set({ phase: e.target.value })}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
          >
            {PHASES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block">
        <span className="text-[10px] text-slate-500">agentId</span>
        <input
          value={step.agentId}
          onChange={(e) => set({ agentId: e.target.value })}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
      </label>

      <label className="block">
        <span className="text-[10px] text-slate-500">subAgentType</span>
        <input
          value={step.subAgentType ?? ""}
          onChange={(e) => set({ subAgentType: e.target.value || undefined })}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
      </label>

      <label className="block">
        <span className="text-[10px] text-slate-500">subGroup</span>
        <input
          value={step.subGroup ?? ""}
          onChange={(e) => set({ subGroup: e.target.value || undefined })}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
      </label>

      <label className="block">
        <span className="text-[10px] text-slate-500">Prompt</span>
        <PromptField value={step.prompt} onChange={(v) => set({ prompt: v })} />
      </label>

      <div>
        <span className="text-[10px] text-slate-500">Transitions</span>
        {(step.transitions ?? []).map((t, i) => (
          <div key={i} className="mt-1 flex items-center gap-1">
            <select
              value={t.goto}
              onChange={(e) => {
                const transitions = [...(step.transitions ?? [])];
                transitions[i] = { ...t, goto: e.target.value };
                set({ transitions });
              }}
              className="flex-1 rounded border border-slate-300 px-2 py-1 text-xs"
            >
              {stepIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
              <option value="$done">$done</option>
            </select>
            <button
              type="button"
              onClick={() => {
                const transitions = (step.transitions ?? []).filter((_, j) => j !== i);
                set({ transitions });
              }}
              className="rounded bg-slate-200 px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-300"
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => set({ transitions: [...(step.transitions ?? []), { goto: "$done" }] })}
          className="mt-1 rounded bg-slate-200 px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-300"
        >
          + Transition
        </button>
      </div>
    </div>
  );
}