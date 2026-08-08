import { useRef, type DragEvent } from "react";

interface PromptFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function insertAtCursor(text: string, value: string, selectionStart: number, selectionEnd: number): string {
  return value.slice(0, selectionStart) + text + value.slice(selectionEnd);
}

export default function PromptField({ value, onChange, placeholder }: PromptFieldProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  const onDrop = (e: DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const text = e.dataTransfer.getData("text/plain");
    if (!text) return;
    const el = ref.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    onChange(insertAtCursor(text, value, start, end));
  };

  const onDragOver = (e: DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
  };

  return (
    <div className="relative">
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onDrop={onDrop}
        onDragOver={onDragOver}
        placeholder={placeholder}
        rows={6}
        className="w-full rounded border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
      />
      <div className="mt-1 text-[10px] text-slate-400">
        Glissez une variable ici ou utilisez le bouton « Insérer ».
      </div>
    </div>
  );
}