export type ActionKind =
  | "choice"
  | "continue"
  | "next_scenario"
  | "repeat"
  | "main_menu"
  | "open_bot"
  | "open_scenario";

export interface Action {
  id: string;
  label: string;
  kind: ActionKind;
  href: string | null;
  scenario_id?: string | null;
}

export interface MiniAppVisual {
  id: string;
  url: string;
  alt: string;
  kind: "logo" | "background" | "football_focus" | "reflection" | "practice" | "progress";
}

export interface Screen {
  node_id: string;
  type: "info" | "choice" | "outcome" | "advice" | "tool" | "completion" | "emergency";
  title: string | null;
  text: string;
  quote: string | null;
  visual: MiniAppVisual | null;
  actions: Action[];
  is_completion: boolean;
  is_mini_app_boundary: boolean;
  stage: number;
  stage_count: number;
}

export interface Training {
  module_id?: string;
  route_mode?: "full" | "standalone";
  scenario_id: string;
  content_version: string;
  scenario_title: string;
  session_id: number;
  revision: number;
  status: string;
  screen: Screen;
}

export interface Situation {
  module_id?: string;
  route_mode?: "full" | "standalone";
  scenario_id: string;
  title: string;
  estimated_minutes: number | null;
  status: "not_started" | "in_progress" | "completed";
  attempt_no: number | null;
}

export interface Progress {
  module_id?: string;
  route_mode?: "full" | "standalone";
  available_count: number;
  completed_count: number;
  current_scenario_id: string | null;
  situations: Situation[];
}

export interface Bootstrap {
  user: { telegram_user_id: number; age_group: string | null };
  ui: {
    start_title: string;
    start_text: string;
    continue_training: string;
    age_prompt: string;
    age_options: Record<string, string>;
    privacy_text: string;
  };
  presentation: {
    start_logo: MiniAppVisual;
    start_background: MiniAppVisual;
    home: MiniAppVisual;
  };
  progress: Progress;
  training: Training | null;
}

export interface TransitionResult {
  status: string;
  training: Training | null;
}
