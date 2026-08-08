import { useEffect, useState } from "react";
import { api, type VariableCategory } from "../api";

interface VariablesPanelProps {
  onInsert: (variable: string) => void;
}

export default function VariablesPanel({ onInsert }: VariablesPanelProps) {
  const [categories, setCategories] = useState<VariableCategory[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getVariables()
      .then(setCategories)
      .catch((err: Error) => setError(err.message));
  }, []);

  const onDragStart = (e: React.DragEvent, variable: string) => {
    e.dataTransfer.setData("text/plain", `{{${variable}}}`);
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div className="p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Variables
      </h2>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {categories.map((cat) => (
        <div key={cat.name} className="mb-3">
          <h3 className="mb-1 text-[10px] font-medium uppercase text-slate-500">{cat.name}</h3>
          <ul className="space-y-1">
            {cat.items.map((item) => (
              <li key={item.name}>
                <button
                  type="button"
                  draggable
                  onDragStart={(e) => onDragStart(e, item.name)}
                  onClick={() => onInsert(`{{${item.name}}}`)}
                  className="w-full rounded bg-slate-800 px-2 py-1 text-left text-xs text-slate-200 hover:bg-slate-700 cursor-grab"
                  title={item.description}
                >
                  <code className="text-blue-300">{`{{${item.name}}}`}</code>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}