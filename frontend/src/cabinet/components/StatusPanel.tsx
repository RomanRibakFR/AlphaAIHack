import { Text } from "../../ui/primitives";
import type { Application, StatusCode } from "../../api/types";
import { REVIEW_STEPS, STATUS_TEXT } from "../content";

/** Внутренние шаги банка, которые клиент видит как один «Рассматриваем заявку». */
const REVIEW: StatusCode[] = ["submitted", "validation", "checks", "scoring"];

type Step = { title: string; state: "done" | "current" | "todo" };

/**
 * Подшаги рассмотрения.
 *
 * Сервер считает их сам и присылает в review_steps — это главный источник:
 * он знает, на каком шаге заявка на самом деле. Свой набор остаётся запасным
 * на случай, если шаги не прислали.
 */
function reviewSteps(app: Application): Step[] {
  if (app.review_steps && app.review_steps.length > 0) {
    return app.review_steps.map((s) => ({
      title: s.title,
      state: s.state === "pending" ? "todo" : s.state,
    }));
  }

  // В REVIEW первым идёт «Отправлена» — отдельного шага для него нет,
  // поэтому сдвигаем на один. Math.max нужен, чтобы сразу после отправки
  // первый шаг уже горел: иначе все три стоят серыми и выглядит,
  // будто заявка зависла.
  const position = Math.max(0, REVIEW.indexOf(app.status.code) - 1);
  return REVIEW_STEPS.map((step, i) => ({
    title: step.title,
    state: i < position ? "done" : i === position ? "current" : "todo",
  }));
}

/**
 * Статус заявки крупно, с объяснением и подшагами.
 *
 * Подшаги показываются только на время рассмотрения: из исследования —
 * клиент не понимает, что происходит, и ждёт звонка. Внутренние названия
 * статусов банка при этом наружу не выходят.
 */
export default function StatusPanel({ app }: { app: Application }) {
  const code = app.status.code;
  const inReview = REVIEW.includes(code);
  const steps = reviewSteps(app);

  return (
    <section className="cb-card">
      {/* Плашку здесь не ставим: она повторяла бы заголовок слово в слово.
          В списке заявок статус показывается плашкой, тут — заголовком. */}
      <Text view="promo-h3" tag="h2">
        {app.status.title}
      </Text>

      <Text
        view="primary-medium"
        color="var(--color-light-text-secondary)"
        style={{ marginTop: 8, maxWidth: 560 }}
      >
        {STATUS_TEXT[code] ?? app.status.hint}
      </Text>

      {inReview && (
        <ol className="cb-steps">
          {steps.map((step) => (
            <li key={step.title} data-state={step.state}>
              <span className="cb-step-dot" />
              <span>{step.title}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
