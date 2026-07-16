import { expect, test } from "@playwright/test";

async function waitForPaint(page: import("@playwright/test").Page) {
  await page.evaluate(
    () => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  );
}

async function expectContentClearsActionPanel(page: import("@playwright/test").Page) {
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  const clearsPanel = await page.evaluate(() => {
    const card = document.querySelector(".screen-card, .quote-card");
    const panel = document.querySelector(".training-actions");
    return Boolean(card && panel && card.getBoundingClientRect().bottom <= panel.getBoundingClientRect().top + 1);
  });
  expect(clearsPanel).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
}

test("live Docker visual acceptance flow", async ({ page }) => {
  const initData = process.env.E2E_INIT_DATA;
  if (!initData) throw new Error("E2E_INIT_DATA is required for the live Docker test");
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

  await page.goto("/");
  await expect(page.getByRole("img", { name: "Фирменный логотип Mental Skills" })).toBeVisible();
  await page.screenshot({ path: "../docs/screenshots/mini-app-v2-start.png", fullPage: true });

  const age = await page.request.patch("/api/v1/me/age", { data: { age_group: "9-12" } });
  expect(age.ok()).toBe(true);
  const restart = await page.request.post("/api/v1/training/restart");
  expect(restart.ok()).toBe(true);

  await page.goto("/home");
  await expect(page.getByRole("navigation", { name: "Главное меню" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Продолжить маршрут" })).toBeVisible();
  await expect.poll(() => page.locator(".app-header img").evaluate((image) => (image as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0);
  const homeLayout = await page.evaluate(() => {
    const card = document.querySelector(".hero-card")?.getBoundingClientRect();
    const action = document.querySelector(".home-action-panel")?.getBoundingClientRect();
    const button = document.querySelector(".home-primary-button")?.getBoundingClientRect();
    const navigation = document.querySelector(".bottom-nav")?.getBoundingClientRect();
    if (!card || !action || !button || !navigation) return null;
    return {
      cardVisiblePixels: Math.max(0, Math.min(card.bottom, action.top) - Math.max(card.top, 0)),
      buttonVisible: button.top >= 0 && button.bottom <= window.innerHeight,
      actionClearsNavigation: action.bottom <= navigation.top + 1,
      navigationClearsSafeArea: navigation.bottom <= window.innerHeight - 23,
      buttonSingleLine: button.height <= 58,
      scrollY: window.scrollY
    };
  });
  expect(homeLayout).toMatchObject({
    buttonVisible: true,
    actionClearsNavigation: true,
    navigationClearsSafeArea: true,
    buttonSingleLine: true,
    scrollY: 0
  });
  expect(homeLayout?.cardVisiblePixels).toBeGreaterThan(180);
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-home-fixed-action.png" });

  await page.getByRole("button", { name: "Продолжить маршрут" }).click();
  await expect(page.getByText("Ситуация 1 из 7")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Я не хочу выходить на игру" })).toBeVisible();
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-polish-scenario-01.png" });

  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByText("Что вы сделаете?")).toBeVisible();
  await page.screenshot({ path: "../docs/screenshots/mini-app-v2-choice.png", fullPage: true });

  await page.getByRole("button", { name: "Все волнуются. Выходи" }).click();
  await page.getByRole("button", { name: "Только не подведи команду" }).click();
  await expect(page.getByText("Что может произойти")).toBeVisible();
  await expect(page.getByLabel("Решение и расходящиеся последствия")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-final-outcome.png" });
  await page.reload();
  await expect(page.getByText("Что может произойти")).toBeVisible();
  await expect(page.getByLabel("Решение и расходящиеся последствия")).toBeVisible();
  expect(await page.evaluate(() => window.scrollY)).toBe(0);

  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByText("Практический совет")).toBeVisible();
  await expect(page.getByLabel("Три шага практического инструмента")).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-final-advice.png" });
  await page.getByRole("button", { name: "Показать готовую фразу" }).click();
  await expect(page.getByText("Готовая фраза")).toBeVisible();
  await expect(page.locator(".advice-quote-card")).toBeVisible();

  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByText("Общий вывод")).toBeVisible();
  await expect(page.getByLabel("Линии сходятся к единому фокусу")).toBeVisible();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByText("Правило трёх вопросов")).toBeVisible();
  await expect(page.getByLabel("Три шага практического инструмента")).toBeVisible();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByText("Ситуация завершена.", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Нейронная сеть завершения")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  expect(await page.evaluate(() => window.scrollX)).toBe(0);
  await expect(page.getByText("Перейти к ситуации 2", { exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Повторить" })).toBeVisible();
  await expect(page.getByRole("button", { name: "На главную", exact: true })).toBeVisible();
  await expectContentClearsActionPanel(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await waitForPaint(page);
  expect(await page.locator(".training-content").evaluate((element) => element.getBoundingClientRect().left)).toBe(0);
  await page.screenshot({ path: "../docs/screenshots/mini-app-final-completion.png" });
  await page.reload();
  await expect(page.getByText("Ситуация завершена.", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Нейронная сеть завершения")).toBeVisible();
  expect(await page.evaluate(() => window.scrollY)).toBe(0);

  await page.getByRole("button", { name: "На главную", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Главное меню" })).toBeVisible();
  await page.getByRole("link", { name: "Прогресс" }).click();
  await expect(page.getByText("Пройдено 1 из 2 доступных")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-final-progress.png" });

  await page.goto("/training");
  await expect(page.getByText("Ситуация завершена.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Перейти к ситуации 2" }).click();
  await expect(page.getByText("Ситуация 2 из 7")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Последние инструкции перед стартом" })).toBeVisible();
  await expect(page.getByLabel("Три смысловых узла перед стартом")).toBeVisible();
  await waitForPaint(page);
  await page.screenshot({ path: "../docs/screenshots/mini-app-polish-scenario-02.png" });
});
