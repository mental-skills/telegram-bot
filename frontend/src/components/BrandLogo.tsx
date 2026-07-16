interface BrandLogoProps {
  size?: "scenario" | "compact" | "header" | "large";
  src?: string;
  alt?: string;
}

export function BrandLogo({
  size = "compact",
  src = "/api/v1/mini-app/assets/brand_logo_official",
  alt = "Фирменный логотип Mental Skills"
}: BrandLogoProps) {
  return (
    <span className={`brand-logo brand-logo-${size}`}>
      <img src={src} alt={alt} />
    </span>
  );
}
