import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Icon, type IconName } from "./Icons";
import { BrandLogo } from "./BrandLogo";

const items: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/home", label: "Главная", icon: "home" },
  { to: "/situations", label: "Ситуации", icon: "situations" },
  { to: "/progress", label: "Прогресс", icon: "progress" },
  { to: "/profile", label: "Профиль", icon: "profile" }
];

export function AppShell({
  children,
  title,
  primaryAction
}: {
  children: ReactNode;
  title?: string;
  primaryAction?: ReactNode;
}) {
  const navigate = useNavigate();
  const isInternal = Boolean(title);
  return (
    <div className={`app-shell ${primaryAction ? "app-shell-with-primary-action" : ""}`}>
      <header className={`app-header ${isInternal ? "app-header-internal" : "app-header-home"}`}>
        {isInternal ? (
          <button className="icon-button" aria-label="Назад на главную" onClick={() => navigate("/home")}>←</button>
        ) : null}
        <BrandLogo size={isInternal ? "compact" : "header"} />
        {isInternal ? <span className="header-spacer" /> : null}
        {title ? <span className="visually-hidden">{title}</span> : null}
      </header>
      {isInternal ? <div className="section-progress" aria-hidden="true"><span /></div> : null}
      <main className="page-content">{children}</main>
      {primaryAction ? <div className="home-action-panel">{primaryAction}</div> : null}
      <nav className="bottom-nav" aria-label="Главное меню">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} className="nav-item">
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function PageTitle({ eyebrow, children }: { eyebrow?: string; children: ReactNode }) {
  return (
    <div className="page-title-block">
      {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
      <h1>{children}</h1>
    </div>
  );
}
