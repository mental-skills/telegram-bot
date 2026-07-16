import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Training } from "../api/contracts";
import { TrainingPage } from "../pages/TrainingPage";

function renderTraining(training: Training) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  client.setQueryData(["training"], training);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/training"]}>
        <TrainingPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const base: Training = {
  scenario_id: "PREMATCH_GAME_REFUSAL_01",
  content_version: "test",
  scenario_title: "Я не хочу выходить на игру",
  session_id: 1,
  revision: 4,
  status: "active",
  screen: {
    node_id: "a2_advice",
    type: "advice",
    title: "Практический совет",
    text: "Сначала назовите состояние, затем задайте один вопрос.",
    quote: "Я вижу, что тебе тревожно. Что поможет сделать первый шаг?",
    visual: {
      id: "premium_three_questions",
      url: "/api/v1/mini-app/assets/premium_three_questions",
      alt: "Схема трёх коротких вопросов",
      kind: "practice"
    },
    actions: [{ id: "continue", label: "Продолжить", kind: "continue", href: null }],
    is_completion: false,
    is_mini_app_boundary: false,
    stage: 4,
    stage_count: 6
  }
};

describe("TrainingPage", () => {
  it("shows advice and quote as separate presentation phases", () => {
    renderTraining(base);
    expect(screen.getByText(base.screen.text)).toBeInTheDocument();
    expect(screen.queryByLabelText("Три шага практического инструмента")).not.toBeInTheDocument();
    expect(screen.queryByText(base.screen.quote!)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Показать готовую фразу" }));
    expect(screen.getByText(base.screen.quote!)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Продолжить" })).toBeInTheDocument();
  });

  it("uses a converging graphic for the summary", () => {
    renderTraining({
      ...base,
      screen: {
        ...base.screen,
        node_id: "summary_main",
        type: "tool",
        title: "Общий вывод",
        quote: null
      }
    });
    expect(screen.getByLabelText("Линии сходятся к единому фокусу")).toBeInTheDocument();
    expect(screen.queryByLabelText("Решение и расходящиеся последствия")).not.toBeInTheDocument();
  });

  it("shows one completion CTA and compact secondary actions", () => {
    renderTraining({
      ...base,
      screen: {
        ...base.screen,
        node_id: "completion",
        type: "completion",
        title: null,
        quote: null,
        actions: [
          { id: "next", label: "Перейти к ситуации 2", kind: "next_scenario", href: null },
          { id: "repeat", label: "Повторить ситуацию", kind: "repeat", href: null },
          { id: "menu", label: "Главное меню", kind: "main_menu", href: null }
        ],
        is_completion: true
      }
    });
    expect(screen.getAllByText("Перейти к ситуации 2")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Повторить ситуацию" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Главное меню" })).toBeInTheDocument();
  });

  it("renders the approved scenario 2 intro and allows continuing", () => {
    renderTraining({
      ...base,
      scenario_id: "PREMATCH_INSTRUCTIONS_02",
      scenario_title: "Последние инструкции перед стартом",
      screen: {
        ...base.screen,
        node_id: "intro",
        type: "info",
        title: "Ситуация 2 из 7. Последние инструкции перед стартом",
        quote: null,
        is_mini_app_boundary: false,
        actions: [{ id: "continue", label: "Продолжить", kind: "continue", href: null }],
        stage: 1
      }
    });
    expect(screen.getByText("Ситуация 2 из 7")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Последние инструкции перед стартом" })).toBeInTheDocument();
    expect(screen.getByLabelText("Три смысловых узла перед стартом")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Продолжить" })).toBeInTheDocument();
  });
});
