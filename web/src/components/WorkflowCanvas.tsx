import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Handle,
  Position,
  useReactFlow,
  type Node,
  type Edge,
  type NodeProps,
  type OnNodesChange,
  type Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { serializeWorkflow, phaseColor, type GraphNode } from "../lib/serialize";
import type { Workflow } from "../api";

interface WorkflowCanvasProps {
  workflow: Workflow;
  selectedStepId: string | null;
  onSelectStep: (stepId: string | null) => void;
  onNodesChange: OnNodesChange;
  onNodeDragStop?: (event: unknown, node: Node, nodes: Node[]) => void;
  onDropTemplate?: (templateId: string, position: { x: number; y: number }) => void;
  onConnect?: (connection: Connection) => void;
}

interface StepNodeData {
  label: string;
  phase: string;
  type: string;
  subGroup?: string;
  subAgentType?: string;
  isTerminal?: boolean;
}

function StepNode({ data, selected }: NodeProps) {
  const d = data as unknown as StepNodeData;
  const color = phaseColor(d.phase);
  return (
    <div
      className={`rounded-lg border-2 bg-white px-3 py-2 shadow-sm min-w-[140px] ${
        selected ? "ring-2 ring-blue-500" : ""
      }`}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !border-2 !border-slate-400 !bg-white" />
      <div className="text-xs font-semibold text-slate-800">{d.label}</div>
      <div className="text-[10px] text-slate-500">
        {d.subAgentType ? `${d.subAgentType} · ` : ""}
        {d.type}
        {d.subGroup ? ` · ${d.subGroup}` : ""}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !border-2 !border-slate-400 !bg-white" />
    </div>
  );
}

function TerminalNode({ data, selected }: NodeProps) {
  const d = data as unknown as StepNodeData;
  return (
    <div
      className={`rounded-full border-2 border-slate-400 bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 ${
        selected ? "ring-2 ring-blue-500" : ""
      }`}
    >
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !border-2 !border-slate-400 !bg-white" />
      {d.label}
    </div>
  );
}

const nodeTypes = { step: StepNode, terminal: TerminalNode };

function CanvasInner({
  workflow,
  onSelectStep,
  onNodesChange,
  onNodeDragStop,
  onDropTemplate,
  onConnect,
}: Omit<WorkflowCanvasProps, "onSelectStep"> & { onSelectStep: (stepId: string | null) => void }) {
  const { screenToFlowPosition } = useReactFlow();
  const { nodes, edges } = useMemo(() => {
    const graph = serializeWorkflow(workflow);
    const nodes: Node[] = graph.nodes.map((n: GraphNode) => ({
      id: n.id,
      position: n.position,
      type: n.data.isTerminal ? "terminal" : "step",
      data: n.data,
    }));
    const edges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: e.animated,
      label: e.label,
      style: e.animated ? { stroke: "#f59e0b" } : undefined,
    }));
    return { nodes, edges };
  }, [workflow]);

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => onSelectStep(node.id === "$done" ? null : node.id),
    [onSelectStep],
  );

  const onPaneClick = useCallback(() => onSelectStep(null), [onSelectStep]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    if (event.dataTransfer.types.includes("application/x-agent-template")) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    }
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      const templateId = event.dataTransfer.getData("application/x-agent-template");
      if (!templateId) return;
      event.preventDefault();
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      onDropTemplate?.(templateId, position);
    },
    [screenToFlowPosition, onDropTemplate],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      minZoom={0.2}
      maxZoom={2.5}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      onNodesChange={onNodesChange}
      onNodeDragStop={onNodeDragStop}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onConnect={onConnect}
    >
      <Background gap={16} />
      <Controls />
    </ReactFlow>
  );
}

export default function WorkflowCanvas(props: WorkflowCanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}