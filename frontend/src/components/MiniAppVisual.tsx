import type { MiniAppVisual as MiniAppVisualData } from "../api/contracts";

interface Props {
  visual: MiniAppVisualData | null;
  context: "home" | "training";
}

export function MiniAppVisual({ visual, context }: Props) {
  if (!visual) return null;
  return (
    <figure
      className={`mini-visual mini-visual-${context} mini-visual-${visual.kind}`}
      data-visual={visual.id}
      aria-label={visual.alt}
    >
      <img src={visual.url} alt="" aria-hidden="true" />
    </figure>
  );
}
