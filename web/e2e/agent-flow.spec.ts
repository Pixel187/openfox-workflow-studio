import { test, expect } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8766";

function demoWorkflow() {
  return {
    metadata: {
      id: "e2e-demo",
      name: "E2E Demo",
      description: "Workflow de test E2E",
      version: "1.0.0",
      color: "#3b82f6",
    },
    entryStep: "s1",
    settings: { maxIterations: 50 },
    steps: [
      {
        id: "s1",
        name: "Étape 1",
        type: "agent",
        phase: "build",
        agentId: "builder",
        prompt: "Fais le travail avec {{workdir}}",
        transitions: [{ goto: "$done" }],
      },
    ],
    startCondition: { type: "always" },
  };
}

test("flux propose → approuver met à jour le workflow et le canvas", async ({
  page,
  request,
}) => {
  const create = await request.post(`${BACKEND}/api/workflows`, {
    data: demoWorkflow(),
  });
  expect(create.status()).toBe(201);

  await page.goto("/");
  await page.getByRole("button", { name: /E2E Demo/ }).click();

  await page.getByPlaceholder("Ex : ajoute une étape de vérification").fill(
    "Ajoute une étape de vérification",
  );
  await page.getByRole("button", { name: "Proposer" }).click();

  await expect(page.getByText("+ s2")).toBeVisible();
  await expect(page.getByText("variables préservées")).toBeVisible();

  await page.getByRole("button", { name: "Approuver" }).click();

  const get = await request.get(`${BACKEND}/api/workflows/e2e-demo`);
  expect(get.status()).toBe(200);
  const data = await get.json();
  expect(data.steps.map((s: { id: string }) => s.id)).toContain("s2");

  await expect(page.getByText("Étape IA")).toBeVisible();
});