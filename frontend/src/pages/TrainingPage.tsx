import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ApiError, getCurrentTraining, startSituation, transition } from "../api/client";
import type { Action, Training } from "../api/contracts";
import { BrandLogo } from "../components/BrandLogo";
import {
  CompletionGraphic,
  ConsequenceGraphic,
  PracticalTipGraphic,
  Scenario01Graphic,
  Scenario02Graphic,
  Scenario03Graphic,
  Scenario04Graphic,
  Scenario05Graphic,
  Scenario06Graphic,
  Scenario07Graphic,
  SummaryGraphic
} from "../components/PurposeGraphics";
import { ErrorPage, LoadingPage } from "../components/StatusPages";

function splitIntroTitle(title: string | null, fallback: string, isIntro: boolean) {
  if (isIntro && title) {
    const match = title.match(/^(Ситуация\s+\d+\s+из\s+\d+)\.\s*(.+)$/i);
    if (match) return { eyebrow: match[1], heading: match[2] };
  }
  return { eyebrow: fallback, heading: title };
}

function ScreenGraphic({ training }: { training: Training }) {
  const { screen } = training;
  if (screen.type === "info") {
    const graphics = {
      PREMATCH_GAME_REFUSAL_01: Scenario01Graphic,
      PREMATCH_INSTRUCTIONS_02: Scenario02Graphic,
      CHILD_ERROR_LOOKS_AT_PARENT_03: Scenario03Graphic,
      CHILD_LEFT_ON_BENCH_04: Scenario04Graphic,
      DISPUTED_REFEREE_DECISION_05: Scenario05Graphic,
      CHILD_SILENT_AFTER_DEFEAT_06: Scenario06Graphic,
      PARENT_RESPONSE_AFTER_VICTORY_07: Scenario07Graphic
    } as const;
    const Graphic = graphics[training.scenario_id as keyof typeof graphics] ?? Scenario01Graphic;
    return <Graphic className="purpose-graphic-intro" />;
  }
  if (screen.type === "outcome") {
    return <ConsequenceGraphic className="purpose-graphic-card" />;
  }
  if (screen.type === "tool" && screen.node_id === "summary_main") {
    return <SummaryGraphic className="purpose-graphic-card" />;
  }
  if (screen.type === "tool") {
    return <PracticalTipGraphic className="purpose-graphic-card purpose-graphic-tip" />;
  }
  if (screen.type === "completion") {
    return <CompletionGraphic className="purpose-graphic-card purpose-graphic-completion" />;
  }
  return null;
}

export function TrainingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["training"], queryFn: getCurrentTraining, retry: false });
  const [showQuote, setShowQuote] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const actionPanelRef = useRef<HTMLDivElement>(null);
  const [actionPanelHeight, setActionPanelHeight] = useState(0);

  useEffect(() => {
    setShowQuote(false);
    setRequestError(null);
    document.documentElement.scrollTop = 0;
    document.documentElement.scrollLeft = 0;
    document.body.scrollTop = 0;
    document.body.scrollLeft = 0;
  }, [query.data?.screen.node_id]);

  useLayoutEffect(() => {
    const panel = actionPanelRef.current;
    if (!panel) {
      setActionPanelHeight(0);
      return;
    }
    const updateHeight = () => setActionPanelHeight(Math.ceil(panel.getBoundingClientRect().height));
    updateHeight();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateHeight);
      return () => window.removeEventListener("resize", updateHeight);
    }
    const observer = new ResizeObserver(updateHeight);
    observer.observe(panel);
    window.addEventListener("resize", updateHeight);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateHeight);
    };
  }, [query.data?.screen.node_id, showQuote]);

  const mutation = useMutation({
    mutationFn: ({ training, optionId }: { training: Training; optionId: string }) => transition(training, optionId),
    onSuccess: async (result) => {
      setRequestError(null);
      if (result.status === "main_menu" || !result.training) {
        await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
        navigate("/home");
        return;
      }
      queryClient.setQueryData(["training"], result.training);
      await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
    },
    onError: async (error) => {
      const detail = error instanceof ApiError ? error.detail : "request_failed";
      if (detail === "stale" || detail === "duplicate") {
        await query.refetch();
        setRequestError("Экран уже обновился. Показано актуальное состояние.");
      } else {
        setRequestError("Не удалось сохранить выбор. Попробуйте ещё раз.");
      }
    }
  });
  const scenarioMutation = useMutation({
    mutationFn: startSituation,
    onSuccess: (nextTraining) => {
      queryClient.setQueryData(["training"], nextTraining);
      setRequestError(null);
    },
    onError: () => setRequestError("Не удалось открыть ситуацию. Попробуйте ещё раз.")
  });

  if (query.isLoading) return <LoadingPage />;
  if (query.isError || !query.data) {
    return <ErrorPage message={query.error?.message} retry={() => void query.refetch()} />;
  }
  const training = query.data;
  const screen = training.screen;
  const displayTitle = splitIntroTitle(screen.title, training.scenario_title, screen.type === "info");
  const quotePhase = screen.type === "advice" && Boolean(screen.quote) && showQuote;
  const completionPrimary = screen.actions.find((action) => action.kind === "next_scenario");
  const completionSecondary = screen.actions.filter((action) => action.kind === "repeat" || action.kind === "main_menu");
  const moduleScenarioActions = screen.actions.filter((action) => action.kind === "open_scenario");
  const moduleHomeAction = screen.actions.find((action) => action.kind === "main_menu");
  const isModuleCompletion = screen.node_id === "module_completion";
  const hasActionPanel = screen.type !== "choice" && !isModuleCompletion;

  const handleAction = (action: Action) => {
    if (action.kind === "main_menu") {
      navigate("/home");
      return;
    }
    if (action.kind === "open_bot" && action.href) {
      window.location.assign(action.href);
      return;
    }
    if (action.kind === "open_scenario" && action.scenario_id) {
      scenarioMutation.mutate(action.scenario_id);
      return;
    }
    mutation.mutate({ training, optionId: action.id });
  };

  return (
    <main
      className="training-page"
      style={{ "--action-panel-height": `${actionPanelHeight}px` } as CSSProperties}
    >
      <header className="training-header">
        <button className="icon-button" aria-label="Назад на главную" onClick={() => navigate("/home")}>←</button>
        <BrandLogo size="scenario" />
        <span className="header-spacer" />
      </header>
      <div className="training-progress" aria-label={`Этап ${screen.stage} из ${screen.stage_count}`}>
        <span style={{ width: `${(screen.stage / screen.stage_count) * 100}%` }} />
      </div>
      <section className="training-content">
        <span className="eyebrow">{displayTitle.eyebrow}</span>
        <h1>{displayTitle.heading ?? (screen.type === "choice" ? "Что вы сделаете?" : training.scenario_title)}</h1>

        {screen.type === "info" && !quotePhase ? (
          <ScreenGraphic training={training} />
        ) : null}

        {quotePhase ? (
          <section className="quote-card advice-quote-card">
            <span className="card-kicker">Готовая фраза</span>
            <blockquote>{screen.quote}</blockquote>
          </section>
        ) : (
          <section className={`screen-card screen-${screen.type}`}>
            {screen.type !== "info" ? <ScreenGraphic training={training} /> : null}
            <p>{screen.text}</p>
            {screen.type !== "advice" && screen.quote ? <blockquote>{screen.quote}</blockquote> : null}
          </section>
        )}

        {isModuleCompletion ? (
          <section className="module-scenario-list" aria-label="Пройденные ситуации">
            <span className="card-kicker">Открыть повторно</span>
            {moduleScenarioActions.map((action, index) => (
              <button
                key={action.id}
                className="module-scenario-button"
                disabled={scenarioMutation.isPending}
                onClick={() => handleAction(action)}
              >
                <span>{index + 1}</span>
                {action.label}
              </button>
            ))}
            {moduleHomeAction ? (
              <button className="primary-button module-home-button" onClick={() => handleAction(moduleHomeAction)}>
                {moduleHomeAction.label}
              </button>
            ) : null}
          </section>
        ) : null}

        {screen.type === "choice" ? (
          <div className="choice-list">
            {screen.actions.map((action, index) => (
              <button key={action.id} className="choice-card" disabled={mutation.isPending} onClick={() => handleAction(action)}>
                <span className="choice-letter">{String.fromCharCode(1040 + index)}</span>
                <span>{action.label}</span>
              </button>
            ))}
          </div>
        ) : null}

        {requestError ? <p className="inline-error" role="alert">{requestError}</p> : null}
      </section>

      {hasActionPanel ? <div
        ref={actionPanelRef}
        className={`training-actions ${screen.type === "completion" ? "training-actions-completion" : ""}`}
      >
        {screen.type === "advice" && screen.quote && !showQuote ? (
          <button className="primary-button" onClick={() => setShowQuote(true)}>Показать готовую фразу</button>
        ) : null}
        {screen.type === "completion" && completionPrimary ? (
          <>
            <button className="primary-button" disabled={mutation.isPending} onClick={() => handleAction(completionPrimary)}>
              {mutation.isPending ? "Сохраняем…" : completionPrimary.label}
            </button>
            <div className="completion-secondary-actions">
              {completionSecondary.map((action) => (
                <button
                  key={action.id}
                  className="completion-secondary-button"
                  disabled={mutation.isPending}
                  onClick={() => handleAction(action)}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </>
        ) : null}
        {(screen.type !== "completion" && (screen.type !== "advice" || showQuote || !screen.quote))
          ? screen.actions.map((action, index) => (
            <button
              key={action.id}
              className={index === 0 && action.kind !== "open_bot" ? "primary-button" : "secondary-button"}
              disabled={mutation.isPending}
              onClick={() => handleAction(action)}
            >
              {mutation.isPending ? "Сохраняем…" : action.label}
            </button>
          ))
          : null}
      </div> : null}
    </main>
  );
}
