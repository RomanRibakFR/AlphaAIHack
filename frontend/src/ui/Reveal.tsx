/** Обёртки появления. Логика — в lib/motion.ts, стили — в ui/motion.css. */
import { Children, type CSSProperties, type ReactNode } from "react";
import { useInView } from "../lib/motion";

type RevealProps = {
  children: ReactNode;
  /** задержка, мс — для ручного каскада */
  delay?: number;
  /** rise — выезжает снизу, grow — подрастает (для крупных карточек) */
  variant?: "rise" | "grow";
  className?: string;
  style?: CSSProperties;
};

export function Reveal({ children, delay = 0, variant = "rise", className, style }: RevealProps) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const base = variant === "grow" ? "mo-reveal-grow" : "mo-reveal";

  return (
    <div
      ref={ref}
      className={[base, className].filter(Boolean).join(" ")}
      data-shown={inView}
      style={{ transitionDelay: `${delay}ms`, ...style }}
    >
      {children}
    </div>
  );
}

/**
 * Каскад: дети появляются по очереди, а не все разом.
 *
 * Важно, что наблюдатель один на контейнер, а не на каждого ребёнка:
 * иначе карточки в одном ряду появлялись бы вразнобой из-за разницы
 * в пару пикселей по высоте.
 */
export function Stagger({
  children,
  step = 70,
  delay = 0,
  variant = "rise",
  className,
  style,
}: RevealProps & { step?: number }) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const base = variant === "grow" ? "mo-reveal-grow" : "mo-reveal";

  return (
    <div ref={ref} className={className} style={style}>
      {Children.map(children, (child, i) => (
        <div
          className={base}
          data-shown={inView}
          style={{ transitionDelay: `${delay + i * step}ms` }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}
