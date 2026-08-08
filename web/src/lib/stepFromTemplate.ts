import type { AgentTemplate, Step } from "../api";

/**
 * Convertit un gabarit d'agent en Step de workflow.
 *
 * L'id est généré `agent-<slug>-<ts>` (slug du nom, timestamp) pour garantir
 * l'unicité. Les champs type/phase/agentId/subAgentType/subGroup/prompt sont
 * copiés depuis le gabarit. La transition par défaut pointe vers `$done`.
 */
export function stepFromTemplate(template: AgentTemplate, ts: number = Date.now()): Step {
  const slug = template.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const step: Step = {
    id: `agent-${slug}-${ts}`,
    name: template.name,
    type: template.type,
    phase: template.phase,
    agentId: template.agentId,
    prompt: template.prompt,
    transitions: [{ goto: "$done" }],
  };
  if (template.subAgentType) step.subAgentType = template.subAgentType;
  if (template.subGroup) step.subGroup = template.subGroup;
  if (template.nudgePrompt) step.nudgePrompt = template.nudgePrompt;
  return step;
}