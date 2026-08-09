import { useCallback, useEffect, useRef } from "react";
import { api } from "../api";

/**
 * Persiste les positions des nœuds avec un debounce (500ms).
 *
 * L'écriture layout est déclenchée pendant le drag (onNodesChange) ; le debounce
 * évite une écriture par frame. Un seul putLayout part après le dernier changement.
 */
export function useDebouncedLayout(workflowId: string | null, delay = 500) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  return useCallback(
    (nodes: { id: string; position: { x: number; y: number } }[]) => {
      if (!workflowId) return;
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        api.putLayout(workflowId, { nodes }).catch(() => {});
      }, delay);
    },
    [workflowId, delay],
  );
}
