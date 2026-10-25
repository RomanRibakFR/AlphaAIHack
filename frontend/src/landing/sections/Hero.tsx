import { useEffect, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { useNavigate } from "react-router-dom";
import { Container, Text } from "../../ui/primitives";
import { useCountUp, useInView } from "../../lib/motion";
import { HERO, STATS } from "../content";

const INVERTED = "var(--color-light-text-primary-inverted)";
const INVERTED_2 = "var(--color-light-text-secondary-inverted)";

/**
 * Этапы заявки — те же, что клиент видит у себя в кабинете.
 *
 * Карточка намеренно без компании, номера и суммы: это не чья-то заявка,
 * а схема пути. Выдуманное ООО с конкретной суммой читалось бы как реальный
 * пример и обещало бы условия, которых банк не называл.
 */
const FLOW = [
  {
    label: "Заявка отправлена",
    hint: "Сумма, срок и цель — остальное банк подставит по ИНН",
    chip: "Отправлена",
    tone: "grey",
  },
  {
    label: "Проверка данных",
    hint: "Сверяем с ЕГРЮЛ, ФНС и бюро кредитных историй",
    chip: "Проверяем",
    tone: "blue",
  },
  {
    label: "Оценка риска",
    hint: "Считаем сумму и ставку по вашим оборотам",
    chip: "Оцениваем",
    tone: "blue",
  },
  {
    label: "Решение принято",
    hint: "Условия в кабинете: принять, подписать, получить деньги",
    chip: "Готово",
    tone: "green",
  },
] as const;

const STEP_MS = 1600;
const RESTART_PAUSE_MS = 2600;

/**
 * Карточка заявки, которая сама проходит путь по кругу.
 *
 * Это не украшение ради украшения: за пять секунд человек видит,
 * из чего состоит продукт, не читая ни строчки текста.
 */
function FlowCard() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const last = active === FLOW.length - 1;
    const timer = setTimeout(
      () => setActive(last ? 0 : active + 1),
      last ? RESTART_PAUSE_MS : STEP_MS,
    );
    return () => clearTimeout(timer);
  }, [active]);

  const current = FLOW[active];

  return (
    <div className="lp-flow mo-enter" style={{ animationDelay: "240ms" }}>
      <div className="lp-flow-head">
        <div>
          <Text view="accent-primary-medium">Путь заявки</Text>
          <Text view="secondary-medium" color="var(--color-light-text-secondary)">
            От анкеты до денег на счёте — обычно пара минут
          </Text>
        </div>
        <span className="lp-flow-chip" data-tone={current.tone}>
          {current.chip}
        </span>
      </div>

      <ol className="lp-flow-steps">
        {FLOW.map((step, i) => (
          <li
            key={step.label}
            data-state={i < active ? "done" : i === active ? "current" : "todo"}
          >
            <span className="lp-flow-dot" />
            <span>
              {step.label}
              {/* Подпись только у текущего шага: иначе карточка превращается
                  в стену текста и перестаёт читаться с одного взгляда. */}
              {i === active && <span className="lp-flow-hint">{step.hint}</span>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Stat({
  value,
  suffix,
  label,
  decimals = 0,
}: {
  value: number;
  suffix: string;
  label: string;
  decimals?: number;
}) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const shown = useCountUp(value, { enabled: inView, duration: 900 });

  return (
    <div className="lp-stat" ref={ref}>
      <Text view="promo-h3" tag="div" color={INVERTED}>
        {shown.toLocaleString("ru-RU", {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })}
        {suffix}
      </Text>
      <Text view="primary-small" color={INVERTED_2} style={{ marginTop: 4 }}>
        {label}
      </Text>
    </div>
  );
}

export default function Hero({ onCalculator }: { onCalculator: () => void }) {
  const navigate = useNavigate();

  return (
    <Container>
      <div className="lp-hero">
        <div>
          <div className="lp-hero-kicker mo-enter">{HERO.kicker}</div>

          <Text view="promo-hero" tag="h1" color={INVERTED} className="mo-enter">
            {HERO.title.map((line) => (
              <div key={line}>{line}</div>
            ))}
          </Text>

          <Text
            view="primary-large"
            color={INVERTED_2}
            className="mo-enter"
            style={{ marginTop: 20, maxWidth: 480, animationDelay: "90ms" }}
          >
            {HERO.subtitle}
          </Text>

          <div className="lp-hero-cta mo-enter" style={{ animationDelay: "160ms" }}>
            <Button view="accent" size={56} className="mo-press" onClick={() => navigate("/login")}>
              {HERO.cta}
            </Button>
            <Button
              view="secondary"
              size={56}
              className="mo-press lp-btn-ghost"
              onClick={onCalculator}
            >
              {HERO.secondary}
            </Button>
          </div>
        </div>

        <FlowCard />
      </div>

      <div className="lp-stats">
        {STATS.map((s) => (
          <Stat key={s.label} {...s} />
        ))}
      </div>
    </Container>
  );
}
