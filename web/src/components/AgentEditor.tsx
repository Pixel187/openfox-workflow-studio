import { useEffect, useState } from "react";
import { api, type AgentTemplate, type AgentTemplatePayload } from "../api";

const COLLECTIONS = ["general", "codage", "redaction", "juridique"];

interface AgentEditorProps {
  /** Gabarit à éditer, ou undefined pour créer. */
  template: AgentTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}

function emptyPayload(): AgentTemplatePayload {
  return {
    id: "",
    name: "",
    description: "",
    collection: "general",
    type: "agent",
    phase: "build",
    agentId: "builder",
    subAgentType: undefined,
    subGroup: "build",
    prompt: "",
    nudgePrompt: undefined,
  };
}

/**
 * Formulaire modal de création / édition d'un gabarit d'agent.
 * POST /api/agent-base à la création, PUT /api/agent-base/{id} en édition.
 * En création, un bouton « Générer avec l'IA » pré-remplit le formulaire
 * via POST /api/agent-base/generate (Ollama).
 */
export default function AgentEditor({ template, onClose, onSaved }: AgentEditorProps) {
  const [payload, setPayload] = useState<AgentTemplatePayload>(
    template ? { ...template } : emptyPayload(),
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [aiDescription, setAiDescription] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState("");

  useEffect(() => {
    setPayload(template ? { ...template } : emptyPayload());
    setError("");
  }, [template]);

  useEffect(() => {
    if (template) return;
    api
      .getModels()
      .then(({ models: list, default_model }) => {
        setModels(list);
        setModel(default_model ?? list[0] ?? "");
      })
      .catch(() => setModels([]));
  }, [template]);

  const set = <K extends keyof AgentTemplatePayload>(key: K, value: AgentTemplatePayload[K]) =>
    setPayload((p) => ({ ...p, [key]: value }));

  /** L'id doit être en kebab-case : lettres minuscules, chiffres, tirets. */
  const idError =
    !template && payload.id !== "" && !/^[a-z0-9][a-z0-9-]*$/.test(payload.id)
      ? "L'identifiant doit être en minuscules (a-z, 0-9, tirets)."
      : "";

  const onGenerate = async () => {
    if (!aiDescription.trim()) return;
    setGenerating(true);
    setError("");
    try {
      const generated = await api.generateAgentTemplate({
        description: aiDescription.trim(),
        collection: payload.collection,
        model: model || undefined,
      });
      setPayload({ ...emptyPayload(), ...generated });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (idError) return;
    setSaving(true);
    setError("");
    try {
      if (template) {
        await api.updateAgentTemplate(template.id, payload);
      } else {
        await api.createAgentTemplate(payload);
      }
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const inputClass =
    "w-full rounded border border-slate-300 px-2 py-1 text-xs text-slate-800 focus:border-blue-400 focus:outline-none";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-lg bg-white p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">
            {template ? "Modifier l'agent" : "Nouvel agent"}
          </h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>

        {error && <p className="mb-2 rounded bg-red-50 px-2 py-1 text-xs text-red-700">{error}</p>}

        {!template && (
          <div className="mb-3 rounded border border-blue-200 bg-blue-50 p-2">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-blue-700">
              Génération assistée par IA
            </p>
            <div className="flex gap-2">
              <input
                className={inputClass}
                placeholder="Décris l'agent en une phrase (ex : audite la conformité RGPD)"
                value={aiDescription}
                onChange={(e) => setAiDescription(e.target.value)}
              />
              <select
                className="w-44 rounded border border-slate-300 px-2 py-1 text-xs"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                aria-label="Modèle IA"
              >
                {models.length === 0 && <option value="">Modèle par défaut</option>}
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={onGenerate}
                disabled={generating || !aiDescription.trim()}
                className="shrink-0 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500 disabled:opacity-40"
              >
                {generating ? "Génération…" : "Générer avec l'IA"}
              </button>
            </div>
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs text-slate-600">
              Identifiant (id)
              <input
                className={inputClass}
                value={payload.id}
                disabled={!!template}
                onChange={(e) => set("id", e.target.value)}
                required
              />
              {idError && <span className="mt-0.5 block text-[10px] text-red-600">{idError}</span>}
            </label>
            <label className="block text-xs text-slate-600">
              Nom
              <input
                className={inputClass}
                value={payload.name}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </label>
          </div>

          <label className="block text-xs text-slate-600">
            Description
            <input
              className={inputClass}
              value={payload.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </label>

          <div className="grid grid-cols-3 gap-3">
            <label className="block text-xs text-slate-600">
              Collection
              <select
                className={inputClass}
                value={payload.collection}
                onChange={(e) => set("collection", e.target.value)}
              >
                {COLLECTIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs text-slate-600">
              Type
              <select
                className={inputClass}
                value={payload.type}
                onChange={(e) => set("type", e.target.value)}
              >
                <option value="agent">agent</option>
                <option value="sub_agent">sub_agent</option>
              </select>
            </label>
            <label className="block text-xs text-slate-600">
              Phase
              <select
                className={inputClass}
                value={payload.phase}
                onChange={(e) => set("phase", e.target.value)}
              >
                <option value="planning">planning</option>
                <option value="build">build</option>
                <option value="verification">verification</option>
                <option value="review">review</option>
              </select>
            </label>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <label className="block text-xs text-slate-600">
              AgentId
              <input
                className={inputClass}
                value={payload.agentId}
                onChange={(e) => set("agentId", e.target.value)}
                required
              />
            </label>
            <label className="block text-xs text-slate-600">
              SubAgentType
              <input
                className={inputClass}
                value={payload.subAgentType ?? ""}
                onChange={(e) =>
                  set("subAgentType", e.target.value === "" ? undefined : e.target.value)
                }
              />
            </label>
            <label className="block text-xs text-slate-600">
              SubGroup
              <input
                className={inputClass}
                value={payload.subGroup}
                onChange={(e) => set("subGroup", e.target.value)}
              />
            </label>
          </div>

          <label className="block text-xs text-slate-600">
            Prompt
            <textarea
              className={`${inputClass} h-32 resize-y font-mono`}
              value={payload.prompt}
              onChange={(e) => set("prompt", e.target.value)}
              required
            />
          </label>

          <label className="block text-xs text-slate-600">
            Nudge prompt (optionnel)
            <textarea
              className={`${inputClass} h-16 resize-y`}
              value={payload.nudgePrompt ?? ""}
              onChange={(e) =>
                set("nudgePrompt", e.target.value === "" ? undefined : e.target.value)
              }
            />
          </label>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded bg-slate-200 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-300"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-500 disabled:opacity-40"
            >
              {saving ? "Enregistrement…" : template ? "Enregistrer" : "Créer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
