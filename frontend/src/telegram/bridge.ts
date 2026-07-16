const PREMIUM_BACKGROUND = "#050607";

function px(value: number | undefined): string {
  return `${Math.max(0, Math.round(value ?? 0))}px`;
}

export function initializeTelegram(): () => void {
  const webApp = window.Telegram?.WebApp;
  const root = document.documentElement;
  const applyTheme = () => {
    root.dataset.theme = "premium-dark";
    webApp?.setHeaderColor(PREMIUM_BACKGROUND);
    webApp?.setBackgroundColor(PREMIUM_BACKGROUND);
    webApp?.setBottomBarColor?.(PREMIUM_BACKGROUND);
  };

  const applyViewport = () => {
    const stableHeight = webApp?.viewportStableHeight
      ?? webApp?.viewportHeight
      ?? window.visualViewport?.height
      ?? window.innerHeight;
    root.style.setProperty("--telegram-viewport-stable-height", px(stableHeight));
    if (typeof webApp?.contentSafeAreaInset?.bottom === "number") {
      root.style.setProperty("--telegram-content-safe-bottom", px(webApp.contentSafeAreaInset.bottom));
    } else {
      root.style.removeProperty("--telegram-content-safe-bottom");
    }
    if (typeof webApp?.safeAreaInset?.bottom === "number") {
      root.style.setProperty("--telegram-safe-bottom", px(webApp.safeAreaInset.bottom));
    } else {
      root.style.removeProperty("--telegram-safe-bottom");
    }
  };

  webApp?.ready();
  webApp?.expand();
  applyTheme();
  applyViewport();
  webApp?.onEvent("themeChanged", applyTheme);
  webApp?.onEvent("viewportChanged", applyViewport);
  webApp?.onEvent("safeAreaChanged", applyViewport);
  webApp?.onEvent("contentSafeAreaChanged", applyViewport);
  window.visualViewport?.addEventListener("resize", applyViewport);
  window.addEventListener("resize", applyViewport);

  return () => {
    webApp?.offEvent("themeChanged", applyTheme);
    webApp?.offEvent("viewportChanged", applyViewport);
    webApp?.offEvent("safeAreaChanged", applyViewport);
    webApp?.offEvent("contentSafeAreaChanged", applyViewport);
    window.visualViewport?.removeEventListener("resize", applyViewport);
    window.removeEventListener("resize", applyViewport);
  };
}
