import { expect, test } from "@playwright/test";

const bootstrap = {
  user: { telegram_user_id: 123, age_group: "9-12" },
  ui: {
    start_title: "Mental Skills — ментальный спортзал",
    start_text: "Образовательный тренажёр решений для родителей юных футболистов.",
    continue_training: "Начать или продолжить маршрут",
    age_prompt: "Выберите возраст ребёнка:",
    age_options: { "6-8": "6–8 лет", "9-12": "9–12 лет", "13-16": "13–16 лет" },
    privacy_text: "Сохраняются Telegram user ID, возраст и прогресс прохождения."
  },
  presentation: {
    start_logo: { id: "logo_horizontal", url: "/mini-logo.svg", alt: "Логотип Mental Skills", kind: "logo" },
    start_background: { id: "neural_lines", url: "/neural-lines.svg", alt: "Нейронные линии", kind: "background" },
    home: { id: "football_focus", url: "/football-focus.svg", alt: "Схема поля", kind: "football_focus" }
  },
  progress: {
    available_count: 7,
    completed_count: 1,
    current_scenario_id: "PREMATCH_GAME_REFUSAL_01",
    situations: [
      { scenario_id: "PREMATCH_GAME_REFUSAL_01", title: "Я не хочу выходить на игру", estimated_minutes: 8, status: "completed", attempt_no: 1 },
      { scenario_id: "PREMATCH_INSTRUCTIONS_02", title: "Последние инструкции перед стартом", estimated_minutes: 8, status: "not_started", attempt_no: null },
      { scenario_id: "CHILD_ERROR_LOOKS_AT_PARENT_03", title: "Ребёнок ошибается и смотрит на родителя", estimated_minutes: 8, status: "not_started", attempt_no: null },
      { scenario_id: "CHILD_LEFT_ON_BENCH_04", title: "Тренер оставляет ребёнка в запасе", estimated_minutes: 8, status: "not_started", attempt_no: null },
      { scenario_id: "DISPUTED_REFEREE_DECISION_05", title: "Судья принимает спорное решение", estimated_minutes: 8, status: "not_started", attempt_no: null },
      { scenario_id: "CHILD_SILENT_AFTER_DEFEAT_06", title: "После поражения ребёнок не хочет разговаривать", estimated_minutes: 8, status: "not_started", attempt_no: null },
      { scenario_id: "PARENT_RESPONSE_AFTER_VICTORY_07", title: "После победы: что сказать ребёнку?", estimated_minutes: 8, status: "not_started", attempt_no: null }
    ]
  },
  training: null
};

for (const width of [320, 390, 520]) {
  test(`main navigation fits ${width}px without horizontal overflow`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.addInitScript(() => {
      const handlers = new Map<string, Set<() => void>>();
      window.Telegram = {
        WebApp: {
          initData: "",
          colorScheme: "dark",
          viewportHeight: 844,
          viewportStableHeight: 844,
          safeAreaInset: { top: 0, right: 0, bottom: 18, left: 0 },
          contentSafeAreaInset: { top: 0, right: 0, bottom: 28, left: 0 },
          ready: () => undefined,
          expand: () => undefined,
          close: () => undefined,
          onEvent: (event, handler) => {
            if (!handlers.has(event)) handlers.set(event, new Set());
            handlers.get(event)?.add(handler);
          },
          offEvent: (event, handler) => handlers.get(event)?.delete(handler),
          openTelegramLink: () => undefined,
          setHeaderColor: () => undefined,
          setBackgroundColor: () => undefined
        }
      };
    });
    await page.route("https://telegram.org/js/telegram-web-app.js", (route) =>
      route.fulfill({ status: 200, contentType: "application/javascript", body: "" })
    );
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/v1/auth/dev") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ authenticated: true, expires_in: 3600 }) });
      } else if (path === "/api/v1/bootstrap") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(bootstrap) });
      } else {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "not_mocked" }) });
      }
    });
    await page.goto("/home");
    await expect(page.getByRole("navigation", { name: "Главное меню" })).toBeVisible();
    await expect(page.getByText("Спокойная поддержка начинается с практики")).toBeVisible();
    await expect(page.getByText("Пройдено 1 из 7 доступных")).toBeVisible();
    await expect(page.getByRole("button", { name: "Продолжить маршрут" })).toBeVisible();
    const initialLayout = await page.evaluate(() => {
      const heading = document.querySelector(".page-title-block");
      const card = document.querySelector(".hero-card");
      const action = document.querySelector(".home-action-panel");
      const button = document.querySelector(".home-primary-button");
      const nav = document.querySelector(".bottom-nav");
      if (!heading || !card || !action || !button || !nav) return null;
      const headingRect = heading.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      const actionRect = action.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();
      const navRect = nav.getBoundingClientRect();
      return {
        scrollY: window.scrollY,
        headingVisible: headingRect.top >= 0 && headingRect.bottom <= actionRect.top,
        cardVisiblePixels: Math.max(0, Math.min(cardRect.bottom, actionRect.top) - Math.max(cardRect.top, 0)),
        buttonVisible: buttonRect.top >= 0 && buttonRect.bottom <= window.innerHeight,
        actionClearsNavigation: actionRect.bottom <= navRect.top + 1,
        buttonSingleLine: buttonRect.height <= 58
      };
    });
    expect(initialLayout).not.toBeNull();
    expect(initialLayout?.scrollY).toBe(0);
    expect(initialLayout?.headingVisible).toBe(true);
    expect(initialLayout?.cardVisiblePixels).toBeGreaterThan(180);
    expect(initialLayout?.buttonVisible).toBe(true);
    expect(initialLayout?.actionClearsNavigation).toBe(true);
    expect(initialLayout?.buttonSingleLine).toBe(true);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
    await page.screenshot({ path: `test-results/home-${width}.png`, fullPage: true });

    await page.addStyleTag({
      content: `
        h1 { font-size: 32px !important; line-height: 1.2 !important; }
        h2 { font-size: 22px !important; line-height: 1.3 !important; }
        p, .route-summary { font-size: 18px !important; line-height: 1.4 !important; }
        button { font-size: 19px !important; line-height: 1.3 !important; }
        .nav-item { font-size: 14px !important; line-height: 1.2 !important; }
      `
    });
    await page.evaluate(() => window.scrollTo(0, 0));
    const scaledLayout = await page.evaluate(() => {
      const heading = document.querySelector(".page-title-block");
      const card = document.querySelector(".hero-card");
      const action = document.querySelector(".home-action-panel");
      const button = document.querySelector(".home-primary-button");
      const nav = document.querySelector(".bottom-nav");
      if (!heading || !card || !action || !button || !nav) return null;
      const headingRect = heading.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      const actionRect = action.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();
      const navRect = nav.getBoundingClientRect();
      return {
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        scrollY: window.scrollY,
        headingVisible: headingRect.top >= 0 && headingRect.bottom <= actionRect.top,
        cardVisiblePixels: Math.max(0, Math.min(cardRect.bottom, actionRect.top) - Math.max(cardRect.top, 0)),
        buttonVisible: buttonRect.top >= 0 && buttonRect.bottom <= window.innerHeight,
        actionClearsNavigation: actionRect.bottom <= navRect.top + 1,
        navigationClearsSafeArea: navRect.bottom <= window.innerHeight - 27,
        buttonSingleLine: buttonRect.height <= 58
      };
    });
    expect(scaledLayout).not.toBeNull();
    expect(scaledLayout?.overflow).toBe(false);
    expect(scaledLayout?.scrollY).toBe(0);
    expect(scaledLayout?.headingVisible).toBe(true);
    expect(scaledLayout?.cardVisiblePixels).toBeGreaterThan(150);
    expect(scaledLayout?.buttonVisible).toBe(true);
    expect(scaledLayout?.actionClearsNavigation).toBe(true);
    expect(scaledLayout?.navigationClearsSafeArea).toBe(true);
    expect(scaledLayout?.buttonSingleLine).toBe(true);

    await page.getByRole("link", { name: "Прогресс" }).click();
    await expect(page.getByText("Пройдено 1 из 7 доступных")).toBeVisible();
    const progressOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(progressOverflow).toBe(false);
  });
}
