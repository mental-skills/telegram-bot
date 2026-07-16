import type { ReactNode } from "react";

export type IconName = "home" | "situations" | "progress" | "profile" | "check" | "arrow";

const paths: Record<IconName, ReactNode> = {
  home: <path d="M3 11.5 12 4l9 7.5v8a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  situations: <path d="M5 4h12a2 2 0 0 1 2 2v13H7a2 2 0 0 1-2-2zm3 4h8M8 12h8M8 16h5" />,
  progress: <path d="M5 20v-5m7 5V9m7 11V4" />,
  profile: <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8m-7 8a7 7 0 0 1 14 0" />,
  check: <path d="m5 12 4 4L19 6" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />
};

export function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
