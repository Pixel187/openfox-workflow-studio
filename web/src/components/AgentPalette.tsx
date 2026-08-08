import { useCallback, useEffect, useState } from "react";
import { api, type AgentTemplate } from "../api";
import AgentEditor from "./AgentEditor";

const COLLECTION_LABELS: Record<string, string> = {
  general: "Général",
  codage: "Codage",
  redaction: "Rédaction",
  juridique: "Juridique",
};

/**
 * Banque d'agents : liste les gabarits réutilisables (GET /api/agent-base),
 * groupés par collection, et les rend draggable vers le canvas (HTML5 dragstart).
 *
 * Le dataTransfer porte l'id du gabarit sous "application/x-agent-template".
 * Boutons d'édition / suppression (CRUD) + création d'un nouvel agent.
 */
export default function AgentPalette() {
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<AgentTemplate | null>(null);
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(() => {
    api
      .getAgentBase()
      .then(setTemplates)
      .catch((err) => setError((err as Error).message));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onDragStart = (event: React.DragEvent, templateId: string) => {
    event.dataTransfer.setData("application/x-agent-template", templateId);
    event.dataTransfer.effectAllowed = "copy";
  };

  const onDelete = async (template: AgentTemplate) => {
    if (!window.confirm(`Supprimer l'agent « ${template.name} » ?`)) return;
    try {
      await api.deleteAgentTemplate(template.id);
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const collections = [...new Set(templates.map((t) => t.collection))].sort();

  return (
    <div className="p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Banque d'agents
        </h3>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="rounded bg-blue-600 px-2 py-0.5 text-[10px] text-white hover:bg-blue-500"
        >
          + Nouvel agent
        </button>
      </div>
      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
      {templates.length === 0 && !error && (
        <p className="text-xs text-slate-400">Chargement…</p>
      )}
      {collections.map((collection) => (
        <section key={collection} className="mb-3">
          <h4 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            {COLLECTION_LABELS[collection] ?? collection}
          </h4>
          <ul className="space-y-2">
            {templates
              .filter((t) => t.collection === collection)
              .map((t) => (
                <li key={t.id} className="group relative">
                  <div
                    draggable
                    onDragStart={(e) => onDragStart(e, t.id)}
                    className="cursor-grab rounded border border-slate-200 bg-slate-50 px-3 py-2 hover:border-blue-400 hover:bg-blue-50 active:cursor-grabbing"
                    title="Glisser sur le canvas pour créer une étape"
                  >
                    <div className="text-xs font-semibold text-slate-800">{t.name}</div>
                    <div className="text-[10px] text-slate-500">{t.description}</div>
                    <div className="mt-1 text-[10px] text-slate-400">
                      {t.type}
                      {t.subAgentType ? ` · ${t.subAgentType}` : ""} · {t.phase}
                    </div>
                  </div>
                  <div className="absolute right-1 top-1 hidden gap-1 group-hover:flex">
                    <button
                      type="button"
                      onClick={() => setEditing(t)}
                      className="rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-600 shadow hover:text-blue-600"
                      title="Modifier"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(t)}
                      className="rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-600 shadow hover:text-red-600"
                      title="Supprimer"
                    >
                      🗑
                    </button>
                  </div>
                </li>
              ))}
          </ul>
        </section>
      ))}
      {(creating || editing) && (
        <AgentEditor
          template={editing}
          onClose={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSaved={() => {
            setCreating(false);
            setEditing(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}