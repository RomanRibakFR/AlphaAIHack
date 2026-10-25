/** Примитивы вёрстки alfabank.ru.
 *
 *  Названия и набор свойств взяты из их собственной модели страницы
 *  (app_state.json главной): CardPure, Grid, Block, TextV2 — это те же
 *  кубики, из которых собрана настоящая главная.
 *  Значения по умолчанию — замеренные на сайте.
 */
import type { CSSProperties, ReactNode } from "react";

/* ——— CardPure: карточка с картинкой-фоном ———
   На сайте это основной строительный блок плиток и бенто. */
export function CardPure({
  width,
  height,
  background,
  backgroundColor,
  backgroundPosition = "center",
  borderRadius = 24,
  href,
  children,
  className,
  style,
}: {
  width?: number | string;
  height?: number | string;
  /** путь к фоновой картинке */
  background?: string;
  backgroundColor?: string;
  backgroundPosition?: string;
  borderRadius?: number;
  href?: string;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const css: CSSProperties = {
    position: "relative",
    width,
    height,
    borderRadius,
    backgroundColor,
    backgroundImage: background ? `url(${background})` : undefined,
    backgroundPosition,
    backgroundSize: "cover",
    backgroundRepeat: "no-repeat",
    overflow: "hidden",
    display: "block",
    textDecoration: "none",
    color: "inherit",
    ...style,
  };

  if (href) {
    return (
      <a className={["alfa-tile", className].filter(Boolean).join(" ")} href={href} style={css}>
        {children}
      </a>
    );
  }
  return (
    <div className={className} style={css}>
      {children}
    </div>
  );
}

/* ——— Grid: сетка с шагом 24px (так на сайте) ——— */
export function Grid({
  columns,
  gap = 24,
  children,
  style,
}: {
  columns: number | string;
  gap?: number;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: typeof columns === "number" ? `repeat(${columns}, 1fr)` : columns,
        gap,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/* ——— Типографика ———
   Размеры ниже — ровно те, что отдаёт alfabank.ru (замерено в браузере).
   promo-* тяжелее продуктовых headline_* из core-components: это маркетинговый слой. */
const TEXT_STYLES = {
  "promo-hero": { fontSize: 48, lineHeight: "52px", fontWeight: 700, letterSpacing: "-0.5px" },
  "promo-h2": { fontSize: 40, lineHeight: "48px", fontWeight: 700, letterSpacing: "-0.4px" },
  "promo-h3": { fontSize: 30, lineHeight: "36px", fontWeight: 700 },
  "promo-card": { fontSize: 22, lineHeight: "26px", fontWeight: 700 },
  "accent-primary-large": { fontSize: 18, lineHeight: "24px", fontWeight: 700 },
  "accent-primary-medium": { fontSize: 16, lineHeight: "24px", fontWeight: 700 },
  "accent-primary-small": { fontSize: 14, lineHeight: "20px", fontWeight: 700 },
  "primary-large": { fontSize: 18, lineHeight: "24px", fontWeight: 400 },
  "primary-medium": { fontSize: 16, lineHeight: "24px", fontWeight: 400 },
  "primary-small": { fontSize: 14, lineHeight: "20px", fontWeight: 400 },
  "secondary-large": { fontSize: 13, lineHeight: "16px", fontWeight: 400 },
  "secondary-medium": { fontSize: 12, lineHeight: "16px", fontWeight: 400 },
  "secondary-small": { fontSize: 11, lineHeight: "16px", fontWeight: 400 },
} satisfies Record<string, CSSProperties>;

export type TextView = keyof typeof TEXT_STYLES;

export const textStyle = (view: TextView): CSSProperties => TEXT_STYLES[view];

export function Text({
  view = "primary-small",
  color,
  weight,
  tag: Tag = "div",
  children,
  style,
  className,
}: {
  view?: TextView;
  /** токен цвета, напр. "var(--color-light-text-secondary)" */
  color?: string;
  weight?: 400 | 500 | 700;
  tag?: "div" | "span" | "p" | "h1" | "h2" | "h3" | "h4";
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <Tag
      className={className}
      style={{ margin: 0, ...TEXT_STYLES[view], ...(weight ? { fontWeight: weight } : null), color, ...style }}
    >
      {children}
    </Tag>
  );
}

/* ——— Контентная колонка 1140px ——— */
export function Container({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div className="alfa-container" style={style}>
      {children}
    </div>
  );
}
