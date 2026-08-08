import { useState } from "react";
import WorkflowList from "./components/WorkflowList";
import WorkflowEditor from "./components/WorkflowEditor";
import { useWorkflowStore } from "./store/workflowStore";

export default function App() {
  const [openId, setOpenId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const loadWorkflow = useWorkflowStore((s) => s.loadWorkflow);
  const reset = useWorkflowStore((s) => s.reset);

  const open = (id: string) => {
    setOpenId(id);
    loadWorkflow(id);
  };

  const back = () => {
    reset();
    setOpenId(null);
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="h-full">
      {openId ? (
        <WorkflowEditor
          workflowId={openId}
          onBack={back}
          onSaved={() => {
            if (openId) loadWorkflow(openId);
            setRefreshKey((k) => k + 1);
          }}
        />
      ) : (
        <WorkflowList onOpen={open} refreshKey={refreshKey} />
      )}
    </div>
  );
}