interface GraphicProps {
  className?: string;
}

function PurposeGraphic({
  src,
  label,
  className = ""
}: GraphicProps & { src: string; label: string }) {
  return (
    <figure className={`purpose-graphic ${className}`} aria-label={label}>
      <img src={src} alt="" aria-hidden="true" />
    </figure>
  );
}

export function HomeRouteGraphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/home-route.svg" label="Маршрут по доступным ситуациям" />;
}

export function Scenario01Graphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/scenario-01.svg" label="Линия выхода с боковой зоны на поле" />;
}

export function Scenario02Graphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/scenario-02.svg" label="Три смысловых узла перед стартом" />;
}

export function ConsequenceGraphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/consequence.svg" label="Решение и расходящиеся последствия" />;
}

export function SummaryGraphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/summary.svg" label="Линии сходятся к единому фокусу" />;
}

export function PracticalTipGraphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/practical-tip.svg" label="Три шага практического инструмента" />;
}

export function CompletionGraphic(props: GraphicProps) {
  return <PurposeGraphic {...props} src="/visuals/completion.svg" label="Нейронная сеть завершения" />;
}
