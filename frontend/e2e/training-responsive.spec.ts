import { expect, test } from "@playwright/test";
import type { Training } from "../src/api/contracts";

const completion: Training = {
  scenario_id: "PREMATCH_GAME_REFUSAL_01",
  content_version: "responsive-test",
  scenario_title: "Я не хочу выходить на игру",
  session_id: 42,
  revision: 9,
  status: "active",
  screen: {
    node_id: "completion",
    type: "completion",
    title: null,
    text: "Ситуация завершена. Ваш выбор сохранён как часть образовательного тренажёра.",
    quote: null,
    visual: null,
    actions: [
      { id: "next", label: "Перейти к ситуации 2", kind: "next_scenario", href: null },
      { id: "repeat", label: "Повторить ситуацию", kind: "repeat", href: null },
      { id: "menu", label: "Главное меню", kind: "main_menu", href: null }
    ],
    is_completion: true,
    is_mini_app_boundary: false,
    stage: 6,
    stage_count: 6
  }
};

for (const width of [320, 390, 520]) {
  test(`completion clears action panel at ${width}px with enlarged Android text`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/v1/auth/dev") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ authenticated: true }) });
      } else if (path === "/api/v1/training/current") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(completion) });
      } else {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "not_mocked" }) });
      }
    });
    await page.goto("/training");
    await expect(page.getByText("Ситуация завершена.", { exact: false })).toBeVisible();
    await page.addStyleTag({
      content: `
        :root { --tg-content-safe-area-inset-bottom: 28px; }
        h1 { font-size: 32px !important; line-height: 1.2 !important; }
        p { font-size: 18px !important; line-height: 1.4 !important; }
        button { font-size: 19px !important; line-height: 1.3 !important; }
      `
    });
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    const layout = await page.evaluate(() => {
      const card = document.querySelector(".screen-card");
      const panel = document.querySelector(".training-actions");
      const buttons = Array.from(document.querySelectorAll(".training-actions button"));
      return {
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        clearsPanel: Boolean(card && panel && card.getBoundingClientRect().bottom <= panel.getBoundingClientRect().top + 1),
        panelAtBottom: Boolean(panel && Math.abs(panel.getBoundingClientRect().bottom - window.innerHeight) <= 1),
        buttonsFit: buttons.every((button) => {
          const rect = button.getBoundingClientRect();
          return rect.left >= 0 && rect.right <= window.innerWidth;
        })
      };
    });
    expect(layout.overflow).toBe(false);
    expect(layout.clearsPanel).toBe(true);
    expect(layout.panelAtBottom).toBe(true);
    expect(layout.buttonsFit).toBe(true);
    await page.screenshot({ path: `test-results/completion-font-${width}.png` });
  });
}
