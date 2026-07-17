import { afterEach, describe, expect, it, vi } from "vitest";
import { initializeTelegram } from "../telegram/bridge";

afterEach(() => {
  delete window.Telegram;
  document.documentElement.removeAttribute("style");
});

describe("initializeTelegram", () => {
  it("publishes stable viewport and safe-area values and follows Telegram events", () => {
    const listeners = new Map<TelegramWebAppEvent, () => void>();
    const webApp: TelegramWebApp = {
      initData: "signed",
      colorScheme: "dark",
      viewportHeight: 700,
      viewportStableHeight: 680,
      safeAreaInset: { top: 0, right: 0, bottom: 18, left: 0 },
      contentSafeAreaInset: { top: 0, right: 0, bottom: 26, left: 0 },
      ready: vi.fn(),
      expand: vi.fn(),
      setHeaderColor: vi.fn(),
      setBackgroundColor: vi.fn(),
      setBottomBarColor: vi.fn(),
      onEvent: vi.fn((event, listener) => listeners.set(event, listener)),
      offEvent: vi.fn((event) => listeners.delete(event))
    };
    window.Telegram = { WebApp: webApp };

    const dispose = initializeTelegram();

    expect(webApp.ready).toHaveBeenCalledOnce();
    expect(webApp.expand).toHaveBeenCalledOnce();
    expect(document.documentElement.style.getPropertyValue("--telegram-viewport-stable-height")).toBe("680px");
    expect(document.documentElement.style.getPropertyValue("--telegram-content-safe-bottom")).toBe("26px");
    expect(document.documentElement.style.getPropertyValue("--telegram-safe-bottom")).toBe("18px");

    webApp.viewportStableHeight = 640;
    webApp.contentSafeAreaInset = { top: 0, right: 0, bottom: 34, left: 0 };
    listeners.get("viewportChanged")?.();
    listeners.get("contentSafeAreaChanged")?.();

    expect(document.documentElement.style.getPropertyValue("--telegram-viewport-stable-height")).toBe("640px");
    expect(document.documentElement.style.getPropertyValue("--telegram-content-safe-bottom")).toBe("34px");

    dispose();
    expect(webApp.offEvent).toHaveBeenCalledWith("viewportChanged", expect.any(Function));
    expect(webApp.offEvent).toHaveBeenCalledWith("contentSafeAreaChanged", expect.any(Function));
  });
});
