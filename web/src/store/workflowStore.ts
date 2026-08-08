import { create } from "zustand";
import { api, type Workflow, type Step, type ValidationReport } from "../api";

interface WorkflowState {
  workflow: Workflow | null;
  etag: string;
  selectedStepId: string | null;
  validation: ValidationReport | null;
  loading: boolean;
  saving: boolean;
  error: string;
  dirty: boolean;

  loadWorkflow: (id: string) => Promise<void>;
  setSelectedStep: (stepId: string | null) => void;
  updateStep: (stepId: string, patch: Partial<Step>) => void;
  addStep: (step: Step) => void;
  removeStep: (stepId: string) => void;
  duplicateStep: (stepId: string) => void;
  moveStep: (stepId: string, direction: "up" | "down") => void;
  connectSteps: (sourceId: string, targetId: string) => void;
  setValidation: (report: ValidationReport | null) => void;
  save: () => Promise<void>;
  validate: () => Promise<void>;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflow: null,
  etag: "",
  selectedStepId: null,
  validation: null,
  loading: false,
  saving: false,
  error: "",
  dirty: false,

  loadWorkflow: async (id: string) => {
    set({ loading: true, error: "" });
    try {
      const { workflow, etag } = await api.getWorkflowWithEtag(id);
      set({ workflow, etag, loading: false, dirty: false, validation: null, selectedStepId: null });
    } catch (err) {
      set({ loading: false, error: (err as Error).message });
    }
  },

  setSelectedStep: (stepId) => set({ selectedStepId: stepId }),

  updateStep: (stepId, patch) => {
    const wf = get().workflow;
    if (!wf) return;
    set({
      workflow: {
        ...wf,
        steps: wf.steps.map((s) => (s.id === stepId ? { ...s, ...patch } : s)),
      },
      dirty: true,
    });
  },

  addStep: (step) => {
    const wf = get().workflow;
    if (!wf) return;
    set({
      workflow: { ...wf, steps: [...wf.steps, step] },
      dirty: true,
      selectedStepId: step.id,
    });
  },

  removeStep: (stepId) => {
    const wf = get().workflow;
    if (!wf) return;
    if (wf.entryStep === stepId) return;
    const steps = wf.steps.filter((s) => s.id !== stepId).map((s) => ({
      ...s,
      transitions: (s.transitions ?? []).filter((t) => t.goto !== stepId),
    }));
    set({
      workflow: { ...wf, steps },
      dirty: true,
      selectedStepId: null,
    });
  },

  duplicateStep: (stepId) => {
    const wf = get().workflow;
    if (!wf) return;
    const source = wf.steps.find((s) => s.id === stepId);
    if (!source) return;
    const copy: Step = {
      ...source,
      id: `${source.id}-copy-${Date.now()}`,
      name: `${source.name} (copie)`,
    };
    set({
      workflow: { ...wf, steps: [...wf.steps, copy] },
      dirty: true,
      selectedStepId: copy.id,
    });
  },

  setValidation: (report) => set({ validation: report }),

  moveStep: (stepId, direction) => {
    const wf = get().workflow;
    if (!wf) return;
    const idx = wf.steps.findIndex((s) => s.id === stepId);
    if (idx === -1) return;
    const swapWith = direction === "up" ? idx - 1 : idx + 1;
    if (swapWith < 0 || swapWith >= wf.steps.length) return;
    const steps = [...wf.steps];
    [steps[idx], steps[swapWith]] = [steps[swapWith], steps[idx]];
    set({ workflow: { ...wf, steps }, dirty: true });
  },

  connectSteps: (sourceId, targetId) => {
    const wf = get().workflow;
    if (!wf) return;
    if (sourceId === targetId) return;
    const source = wf.steps.find((s) => s.id === sourceId);
    if (!source) return;
    const transitions = source.transitions ?? [];
    if (transitions.some((t) => t.goto === targetId)) return;
    set({
      workflow: {
        ...wf,
        steps: wf.steps.map((s) =>
          s.id === sourceId ? { ...s, transitions: [...transitions, { goto: targetId }] } : s,
        ),
      },
      dirty: true,
    });
  },

  save: async () => {
    const { workflow, etag } = get();
    if (!workflow) return;
    set({ saving: true, error: "" });
    try {
      const saved = await api.updateWorkflow(workflow.metadata.id, workflow, etag);
      set({ workflow: saved, saving: false, dirty: false });
    } catch (err) {
      set({ saving: false, error: (err as Error).message });
    }
  },

  validate: async () => {
    const { workflow } = get();
    if (!workflow) return;
    try {
      const report = await api.validateWorkflow(workflow.metadata.id);
      set({ validation: report });
    } catch (err) {
      set({ error: (err as Error).message });
    }
  },

  reset: () =>
    set({
      workflow: null,
      etag: "",
      selectedStepId: null,
      validation: null,
      loading: false,
      saving: false,
      error: "",
      dirty: false,
    }),
}));