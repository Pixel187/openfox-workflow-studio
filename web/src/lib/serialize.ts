import type { Workflow } from "../api";

export interface GraphNode {
  id: string;
  position: { x: number; y: number };
  data: {
    label: string;
    phase: string;
    type: string;
    subGroup?: string;
    subAgentType?: string;
    isTerminal?: boolean;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  animated?: boolean;
  label?: string;
}

const PHASE_COLORS: Record<string, string> = {
  build: "#3b82f6",
  generate: "#10b981",
  verification: "#8b5cf6",
  review: "#f97316",
};

const PHASE_ORDER = ["build", "generate", "verification", "review"];

export function phaseColor(phase: string): string {
  return PHASE_COLORS[phase] ?? "#64748b";
}

export function serializeWorkflow(wf: Workflow): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const steps = wf.steps ?? [];
  const byPhase = new Map<string, typeof steps>();
  for (const step of steps) {
    const list = byPhase.get(step.phase) ?? [];
    list.push(step);
    byPhase.set(step.phase, list);
  }
  const phases = [...byPhase.keys()].sort((a, b) => {
    const ia = PHASE_ORDER.indexOf(a);
    const ib = PHASE_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const COL_X = 220;
  const COL_Y = 140;

  phases.forEach((phase, col) => {
    const list = byPhase.get(phase)!;
    list.forEach((step, row) => {
      nodes.push({
        id: step.id,
        position: step.position ?? { x: col * COL_X, y: row * COL_Y },
        data: {
          label: step.name,
          phase: step.phase,
          type: step.type,
          subGroup: step.subGroup,
          subAgentType: step.subAgentType,
        },
      });
    });
  });

  const hasDone = steps.some((s) => (s.transitions ?? []).some((t) => t.goto === "$done"));
  if (hasDone) {
    nodes.push({
      id: "$done",
      position: { x: phases.length * COL_X, y: 0 },
      data: { label: "$done", phase: "terminal", type: "terminal", isTerminal: true },
    });
  }

  steps.forEach((s) => {
    (s.transitions ?? []).forEach((t, i) => {
      const target = t.goto;
      const sourceIdx = steps.findIndex((x) => x.id === s.id);
      const targetIdx = steps.findIndex((x) => x.id === target);
      const isLoop = targetIdx !== -1 && targetIdx <= sourceIdx;
      edges.push({
        id: `${s.id}-${target}-${i}`,
        source: s.id,
        target,
        animated: isLoop,
        label: isLoop ? "loop" : undefined,
      });
    });
  });

  return { nodes, edges };
}

export function deserializeWorkflow(
  wf: Workflow,
  nodes: GraphNode[],
): Workflow {
  const positions = new Map(nodes.map((n) => [n.id, n.position]));
  return {
    ...wf,
    steps: (wf.steps ?? []).map((s) => {
      const pos = positions.get(s.id);
      return pos ? { ...s, position: pos } : s;
    }),
  };
}