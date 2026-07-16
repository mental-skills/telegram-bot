import { BrandLogo } from "./BrandLogo";

export function LoadingPage() {
  return (
    <main className="status-page" aria-live="polite">
      <div className="loader" />
      <BrandLogo />
      <p>Загружаем тренажёр…</p>
    </main>
  );
}

export function ErrorPage({ message, retry }: { message?: string; retry: () => void }) {
  return (
    <main className="status-page">
      <div className="status-symbol">!</div>
      <BrandLogo />
      <h1>Не удалось загрузить приложение</h1>
      <p>{message ?? "Попробуйте ещё раз. Сохранённый прогресс не изменён."}</p>
      <button className="primary-button" onClick={retry}>Повторить</button>
    </main>
  );
}

export function OfflinePage({ retry }: { retry: () => void }) {
  return (
    <main className="status-page">
      <div className="status-symbol offline-symbol">⌁</div>
      <BrandLogo />
      <h1>Нет соединения</h1>
      <p>Новый выбор не будет сохранён без связи. Проверьте интернет и повторите запрос.</p>
      <button className="primary-button" onClick={retry}>Проверить соединение</button>
    </main>
  );
}
