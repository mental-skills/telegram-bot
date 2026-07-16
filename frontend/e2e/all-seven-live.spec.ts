import { expect, test, type Page } from "@playwright/test";

const scenarios = [
  ["Реакция на ошибку", "Ситуация 3 из 7", "all-7-scenario-03.png"],
  ["Начинаю матч в запасе", "Ситуация 4 из 7", "all-7-scenario-04.png"],
  ["Спорное решение судьи", "Ситуация 5 из 7", "all-7-scenario-05.png"],
  ["Не хочу обсуждать матч", "Ситуация 6 из 7", "all-7-scenario-06.png"],
  ["После победы", "Ситуация 7 из 7", "all-7-scenario-07.png"]
] as const;

async function installTelegram(page: Page, initData: string) {
  await page.route("https://telegram.org/js/telegram-web-app.js", (route) =>
    route.fulfill({ contentType: "application/javascript", body: "" })
  );
  await page.addInitScript((signedInitData) => {
    Object.defineProperty(window, "Telegram", {
      value: {
        WebApp: {
          initData: signedInitData,
          colorScheme: "dark",
          viewportHeight: 844,
          viewportStableHeight: 844,
          safeAreaInset: { top: 0, right: 0, bottom: 18, left: 0 },
          contentSafeAreaInset: { top: 0, right: 0, bottom: 24, left: 0 },
          ready: () => undefined,
          expand: () => undefined,
          setHeaderColor: () => undefined,
          setBackgroundColor: () => undefined,
          setBottomBarColor: () => undefined,
          onEvent: () => undefined,
          offEvent: () => undefined
        }
      },
      configurable: true
    });
  }, initData);
}

test("actual Docker API renders scenarios 3-7 and module completion", async ({ page }) => {
  const initData = process.env.E2E_INIT_DATA;
  test.skip(!initData, "E2E_INIT_DATA is required for the live Docker test");
  if (!initData) return;
  await page.setViewportSize({ width: 390, height: 844 });
  await installTelegram(page, initData);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Начать" })).toBeVisible();
  const age = await page.request.patch("/api/v1/me/age", { data: { age_group: "9-12" } });
  expect(age.ok()).toBe(true);

  for (const [cardTitle, eyebrow, screenshot] of scenarios) {
    await page.goto("/situations");
    await page.getByText(cardTitle, { exact: true }).click();
    await expect(page.getByText(eyebrow, { exact: true })).toBeVisible();
    await page.waitForFunction(() =>
      Array.from(document.images).every((image) => image.complete && image.naturalWidth > 0)
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth
      )
    ).toBe(true);
    await page.screenshot({ path: `../docs/screenshots/${screenshot}` });
  }

  let training = await page.request.post("/api/v1/training/restart").then((response) => {
    expect(response.ok()).toBe(true);
    return response.json();
  });
  for (let safety = 0; safety < 220 && training.screen.node_id !== "module_completion"; safety += 1) {
    const actions = training.screen.actions as Array<{ id: string; kind: string }>;
    let action = actions[0];
    if (training.screen.node_id === "start_choice") action = actions.find((item) => item.id === "a") ?? action;
    else if (training.screen.node_id === "a_choice") action = actions.find((item) => item.id === "a1") ?? action;
    const response = await page.request.post(
      `/api/v1/training/sessions/${training.session_id}/transitions`,
      { data: { revision: training.revision, option_id: action.id } }
    );
    expect(response.ok(), await response.text()).toBe(true);
    training = (await response.json()).training;
  }
  expect(training.screen.node_id).toBe("module_completion");
  await page.goto("/training");
  await expect(page.getByRole("heading", { name: "Образовательный тренажёр завершён" })).toBeVisible();
  await expect(page.getByText("Открыть повторно")).toBeVisible();
  await page.waitForFunction(() =>
    Array.from(document.images).every((image) => image.complete && image.naturalWidth > 0)
  );
  await page.screenshot({ path: "../docs/screenshots/all-7-module-completion.png", fullPage: true });
});
