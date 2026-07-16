import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getBootstrap, restartTraining, setAge, startOrContinue, startSituation } from "../api/client";
import type { Bootstrap, Situation, Training } from "../api/contracts";
import { AppShell, PageTitle } from "../components/AppShell";
import { BrandLogo } from "../components/BrandLogo";
import { Icon } from "../components/Icons";
import { HomeRouteGraphic } from "../components/PurposeGraphics";
import { ErrorPage, LoadingPage } from "../components/StatusPages";

export function useBootstrap() {
  return useQuery({ queryKey: ["bootstrap"], queryFn: getBootstrap });
}

function BootstrapState({ children }: { children: (data: Bootstrap) => React.ReactNode }) {
  const query = useBootstrap();
  if (query.isLoading) return <LoadingPage />;
  if (query.isError || !query.data) {
    return <ErrorPage message={query.error?.message} retry={() => void query.refetch()} />;
  }
  return children(query.data);
}

export function EntryPage() {
  return <BootstrapState>{(data) => data.user.age_group ? <HomeContent data={data} /> : <StartContent data={data} />}</BootstrapState>;
}

function StartContent({ data }: { data: Bootstrap }) {
  const navigate = useNavigate();
  return (
    <main className="start-page">
      <div className="start-glow" />
      <img className="start-neural-lines" src={data.presentation.start_background.url} alt="" aria-hidden="true" />
      <BrandLogo
        size="large"
        src={data.presentation.start_logo.url}
        alt={data.presentation.start_logo.alt}
      />
      <div className="start-copy">
        <span className="eyebrow">Тренажёр для родителей футболистов</span>
        <h1>{data.ui.start_title}</h1>
        <p>{data.ui.start_text}</p>
      </div>
      <button className="primary-button sticky-action" onClick={() => navigate("/age")}>Начать</button>
    </main>
  );
}

export function AgePage() {
  const query = useBootstrap();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: setAge,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      navigate("/home");
    }
  });
  if (query.isLoading) return <LoadingPage />;
  if (query.isError || !query.data) return <ErrorPage message={query.error?.message} retry={() => void query.refetch()} />;
  const data = query.data;
  return (
    <main className="simple-page">
      <PageTitle eyebrow="Настройка">{data.ui.age_prompt}</PageTitle>
      <p className="secondary-text">Возраст помогает показать утверждённую версию текста ситуации.</p>
      <div className="age-list">
        {Object.entries(data.ui.age_options).map(([value, label], index) => (
          <button key={value} className="age-card" onClick={() => mutation.mutate(value)} disabled={mutation.isPending}>
            <span className="age-number">{index + 1}</span>
            <span><strong>{label}</strong><small>{["Младший", "Средний", "Старший"][index]} возраст</small></span>
            <Icon name="arrow" />
          </button>
        ))}
      </div>
      {mutation.isError ? <p className="inline-error">Не удалось сохранить возраст.</p> : null}
    </main>
  );
}

export function HomePage() {
  return <BootstrapState>{(data) => <HomeContent data={data} />}</BootstrapState>;
}

function HomeContent({ data }: { data: Bootstrap }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: startOrContinue,
    onSuccess: (training) => {
      queryClient.setQueryData(["training"], training);
      navigate("/training");
    }
  });
  const current = data.progress.situations.find((item) => item.scenario_id === data.progress.current_scenario_id);
  const routeStarted = Boolean(data.training)
    || data.progress.completed_count > 0
    || data.progress.situations.some((item) => item.status === "in_progress");
  return (
    <AppShell primaryAction={(
      <button className="primary-button home-primary-button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending ? "Открываем…" : routeStarted ? "Продолжить маршрут" : "Начать маршрут"}
      </button>
    )}>
      <PageTitle eyebrow="Ментальный спортзал">Спокойная поддержка начинается с практики</PageTitle>
      <section className="hero-card">
        <span className="card-kicker">Ваш маршрут</span>
        <h2>{current?.title ?? data.progress.situations[0]?.title}</h2>
        <HomeRouteGraphic className="purpose-graphic-home" />
        <p>{data.training ? "Продолжите с сохранённого экрана." : "Пройдите ситуацию и заберите практическую фразу."}</p>
        <div className="route-summary">
          <span>Пройдено <strong>{data.progress.completed_count}</strong> из <strong>{data.progress.available_count}</strong> доступных</span>
        </div>
      </section>
      {mutation.isError ? <p className="inline-error">Не удалось открыть ситуацию. Попробуйте снова.</p> : null}
    </AppShell>
  );
}

function SituationCard({ situation, current, onOpen }: { situation: Situation; current: boolean; onOpen?: () => void }) {
  const labels = { not_started: "Не начата", in_progress: "В процессе", completed: "Завершена" };
  return (
    <article className={`situation-card ${current ? "current" : ""} ${onOpen ? "interactive" : ""}`} onClick={onOpen}>
      <div className={`status-dot ${situation.status}`}><Icon name={situation.status === "completed" ? "check" : "situations"} size={20} /></div>
      <div>
        <span className="card-kicker">{labels[situation.status]}</span>
        <h2>{situation.title}</h2>
        {situation.estimated_minutes ? <p>{situation.estimated_minutes} минут</p> : null}
      </div>
    </article>
  );
}

export function SituationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: startSituation,
    onSuccess: (training) => {
      queryClient.setQueryData(["training"], training);
      navigate("/training");
    }
  });
  return <BootstrapState>{(data) => (
      <AppShell title="Ситуации">
        <PageTitle eyebrow="Доступно сейчас">Семь футбольных ситуаций</PageTitle>
        <div className="card-list">
          {data.progress.situations.map((item) => <SituationCard key={item.scenario_id} situation={item} current={item.scenario_id === data.progress.current_scenario_id} onOpen={() => mutation.mutate(item.scenario_id)} />)}
        </div>
      </AppShell>
    )}</BootstrapState>;
}

export function ProgressPage() {
  return <BootstrapState>{(data) => {
    const current = data.progress.situations.find((item) => item.scenario_id === data.progress.current_scenario_id);
    return (
      <AppShell title="Прогресс">
        <PageTitle eyebrow="Ваш путь">Прогресс тренажёра</PageTitle>
        <section className="progress-card">
          <p className="progress-copy">Пройдено <strong>{data.progress.completed_count}</strong> из <strong>{data.progress.available_count}</strong> доступных</p>
          <HomeRouteGraphic className="purpose-graphic-progress" />
          <div className="two-step-progress" aria-label={`${data.progress.completed_count} из ${data.progress.available_count} завершено`}>
            {data.progress.situations.map((item, index) => (
              <div key={item.scenario_id} className="step-wrap">
                <span className={`step ${item.status}`}>{item.status === "completed" ? <Icon name="check" size={18} /> : index + 1}</span>
                {index < data.progress.situations.length - 1 ? <span className={`step-line ${item.status === "completed" ? "complete" : ""}`} /> : null}
              </div>
            ))}
          </div>
          <p className="secondary-text">Текущая ситуация: {current?.title ?? "маршрут ещё не начат"}</p>
        </section>
        <section className="surface-card">
          <span className="card-kicker">Текущая ситуация</span>
          <h2>{current?.title ?? "Маршрут ещё не начат"}</h2>
        </section>
        <div className="card-list compact">
          {data.progress.situations.map((item) => <SituationCard key={item.scenario_id} situation={item} current={item.scenario_id === data.progress.current_scenario_id} />)}
        </div>
      </AppShell>
    );
  }}</BootstrapState>;
}

export function ProfilePage() {
  const query = useBootstrap();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const restart = useMutation({
    mutationFn: restartTraining,
    onSuccess: async (training: Training) => {
      queryClient.setQueryData(["training"], training);
      await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      navigate("/training");
    }
  });
  if (query.isLoading) return <LoadingPage />;
  if (query.isError || !query.data) return <ErrorPage message={query.error?.message} retry={() => void query.refetch()} />;
  const data = query.data;
  return (
    <AppShell title="Профиль">
      <PageTitle eyebrow="Настройки">Профиль</PageTitle>
      <section className="surface-card profile-row"><span>Возраст ребёнка</span><strong>{data.user.age_group ? `${data.user.age_group} лет` : "Не выбран"}</strong></section>
      <button className="secondary-button" onClick={() => navigate("/age")}>Изменить возраст</button>
      <button className="secondary-button danger-button" onClick={() => {
        if (window.confirm("Начать маршрут заново? Текущая попытка будет закрыта.")) restart.mutate();
      }}>Начать заново</button>
      <section className="privacy-card"><h2>Конфиденциальность</h2><p>{data.ui.privacy_text}</p></section>
    </AppShell>
  );
}
