import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Training } from "../api/contracts";
import { TrainingPage } from "../pages/TrainingPage";

describe("module completion copy", () => {
  it("does not show editorial fixation markers", () => {
    const training: Training = {
      scenario_id: "PARENT_RESPONSE_AFTER_VICTORY_07",
      content_version: "test",
      scenario_title: "После победы: что сказать ребёнку?",
      session_id: 7,
      revision: 1,
      status: "completed",
      screen: {
        node_id: "module_completion",
        type: "completion",
        title: "Образовательный тренажёр завершён",
        text: "Пройдены все семь ситуаций.\n\nРадость — вклад — развитие.",
        quote: null,
        visual: null,
        actions: [{ id: "home", label: "Главное меню", kind: "main_menu", href: null }],
        is_completion: true,
        is_mini_app_boundary: false,
        stage: 8,
        stage_count: 8
      }
    };
    const queryClient = new QueryClient({
      defaultOptions: { queries: { staleTime: Infinity, retry: false } }
    });
    queryClient.setQueryData(["training"], training);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/training"]}>
          <TrainingPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText(/Радость — вклад — развитие\./)).toBeInTheDocument();
    expect(screen.queryByText("Итоговая фиксация")).not.toBeInTheDocument();
    expect(screen.queryByText(/редакторский источник истины/)).not.toBeInTheDocument();
    expect(screen.queryByText("#")).not.toBeInTheDocument();
    expect(screen.queryByText("---")).not.toBeInTheDocument();
  });
});
