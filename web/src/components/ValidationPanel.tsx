import { useWorkflowStore } from "../store/workflowStore";

export default function ValidationPanel() {
  const validation = useWorkflowStore((s) => s.validation);
  if (!validation) return null;

  const { valid, errors, warnings } = validation;
  return (
    <div
      className={`rounded border px-3 py-2 text-xs ${
        valid ? "border-green-300 bg-green-50 text-green-800" : "border-red-300 bg-red-50 text-red-800"
      }`}
    >
      <div className="font-semibold">{valid ? "Workflow valide" : "Workflow invalide"}</div>
      {errors.length > 0 && (
        <ul className="mt-1 list-disc pl-4">
          {errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      {warnings.length > 0 && (
        <ul className="mt-1 list-disc pl-4 text-amber-700">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}