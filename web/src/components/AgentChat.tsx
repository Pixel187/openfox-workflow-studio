import { useEffect, useState } from "react";
import { api, type ProposalResponse } from "../api";
import { useWorkflowStore } from "../store/workflowStore";

interface AgentChatProps {
  onApplied: () => void;
}

export default function AgentChat({ onApplied }: AgentChatProps) {
  const workflow = useWorkflowStore((s) => s.workflow);
  const selectedStepId = useWorkflowStore((s) => s.selectedStepId);
  const [instruction, setInstruction] = useState("");
  const [scope, setScope] = useState<"workflow" | "step" | "prompt">("workflow");
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState("");
  const [proposal, setProposal] = useState<ProposalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getModels()
      .then((r) => {
        setModels(r.models);
        const preferred = r.default_model
          ? r.models.find((m) => m === r.default_model || m.startsWith(`${r.default_model}:`))
          : undefined;
        setModel(preferred ?? r.models[0] ?? "");
      })
      .catch(() => setModels([]));
  }, []);

  if (!workflow) return null;

  const propose = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setError("");
    setProposal(null);
    try {
      const result = await api.propose({
        workflow_id: workflow.metadata.id,
        scope,
        step_id: scope === "workflow" ? undefined : selectedStepId ?? undefined,
        instruction,
        model: model || undefined,
      });
      setProposal(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    if (!proposal) return;
    setLoading(true);
    setError("");
    try {
      await api.apply(proposal.proposal_id);
      setProposal(null);
      setInstruction("");
      onApplied();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const discard = async () => {
    if (!proposal) return;
    try {
      await api.discard(proposal.proposal_id);
    } catch {
      /* la proposition peut déjà être expirée */
    }
    setProposal(null);
  };

  const diffLines = proposal
    ? [
        ...proposal.diff.added.map((id) => ({ kind: "added", text: `+ ${id}` })),
        ...proposal.diff.removed.map((id) => ({ kind: "removed", text: `- ${id}` })),
        ...proposal.diff.modified.map((id) => ({ kind: "modified", text: `~ ${id}` })),
      ]
    : [];

  return (
    <div className="flex h-full flex-col p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Assistant IA
      </h2>

      <label className="block">
        <span className="text-[10px] text-slate-500">Portée</span>
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as typeof scope)}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        >
          <option value="workflow">Workflow entier</option>
          <option value="step">Étape (canvas)</option>
          <option value="prompt">Prompt seul</option>
        </select>
      </label>

      {models.length > 0 && (
        <label className="mt-2 block">
          <span className="text-[10px] text-slate-500">Modèle</span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
          >
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="mt-2 block">
        <span className="text-[10px] text-slate-500">Instruction</span>
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          placeholder="Ex : ajoute une étape de vérification"
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
      </label>

      <button
        type="button"
        onClick={propose}
        disabled={loading || !instruction.trim()}
        className="mt-2 rounded bg-indigo-600 px-3 py-1.5 text-xs text-white hover:bg-indigo-500 disabled:opacity-50"
      >
        {loading ? "En cours…" : "Proposer"}
      </button>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {proposal && (
        <div className="mt-3 flex-1 overflow-y-auto rounded border border-slate-200 bg-white p-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase text-slate-500">Diff</span>
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] ${
                proposal.preserves_vars
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {proposal.preserves_vars ? "variables préservées" : "variables perdues"}
            </span>
          </div>
          {proposal.lost_vars.length > 0 && (
            <p className="mb-1 text-[10px] text-red-600">
              Perdues : {proposal.lost_vars.join(", ")}
            </p>
          )}
          <ul className="space-y-0.5 font-mono text-[10px]">
            {diffLines.length === 0 && <li className="text-slate-400">Aucune modification</li>}
            {diffLines.map((l, i) => (
              <li
                key={i}
                className={
                  l.kind === "added"
                    ? "text-green-700"
                    : l.kind === "removed"
                      ? "text-red-600"
                      : "text-amber-600"
                }
              >
                {l.text}
              </li>
            ))}
          </ul>
          {!proposal.validation.valid && (
            <ul className="mt-2 list-disc pl-4 text-[10px] text-red-600">
              {proposal.validation.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={apply}
              disabled={loading || !proposal.validation.valid || !proposal.preserves_vars}
              className="flex-1 rounded bg-green-600 px-2 py-1 text-[10px] text-white hover:bg-green-500 disabled:opacity-40"
            >
              Approuver
            </button>
            <button
              type="button"
              onClick={discard}
              disabled={loading}
              className="flex-1 rounded bg-slate-300 px-2 py-1 text-[10px] text-slate-700 hover:bg-slate-400"
            >
              Rejeter
            </button>
          </div>
        </div>
      )}
    </div>
  );
}