import { useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { ActionCode, Application, FieldProblem } from "../api/types";

const LABEL: Record<ActionCode, string> = {
  edit: "Редактировать",
  submit: "Отправить в банк",
  withdraw: "Отозвать заявку",
  accept: "Принять предложение",
  decline: "Отказаться от предложения",
  sign: "Подписать договор",
};

/** Ручек нет: бэкенд отдаёт эти действия в available_actions, а POST-эндпоинтов не завёл. */
const NO_ENDPOINT: ActionCode[] = ["accept", "decline", "sign"];

type Props = {
  app: Application;
  /** Пришла обновлённая заявка — экран перерисует себя. */
  onDone: (updated: Application) => void;
  /** 422 от submit: какие поля подсветить в форме. */
  onProblems: (problems: FieldProblem[]) => void;
};

export default function Actions({ app, onDone, onProblems }: Props) {
  const [busy, setBusy] = useState<ActionCode | null>(null);
  const [error, setError] = useState<string | null>(null);

  // заявку изменили (например, дозаполнили черновик) — прошлая жалоба уже не актуальна
  useEffect(() => setError(null), [app.updated_at]);

  // "edit" — это не кнопка, а признак, что черновик ещё можно править (форму рисует DraftForm)
  const actions = app.available_actions.filter((a) => a !== "edit");

  async function run(action: ActionCode) {
    setBusy(action);
    setError(null);
    onProblems([]);
    try {
      if (action === "submit") onDone(await api.submit(app.id));
      else if (action === "withdraw") onDone(await api.withdraw(app.id));
    } catch (e) {
      const err = e as ApiError;
      setError(err.message);
      if (err.problems.length > 0) onProblems(err.problems);
    } finally {
      setBusy(null);
    }
  }

  if (actions.length === 0) {
    return (
      <section>
        <h3>Действия</h3>
        <p className="muted">Для этого статуса действий у клиента нет.</p>
      </section>
    );
  }

  return (
    <section>
      <h3>Действия</h3>
      {actions.map((action) =>
        NO_ENDPOINT.includes(action) ? (
          <p key={action}>
            <button disabled title="Нужен эндпоинт на бэкенде">
              {LABEL[action]}
            </button>{" "}
            <span className="muted">
              нет ручки <code>POST /api/applications/{"{id}"}/{action}</code>
            </span>
          </p>
        ) : (
          <p key={action}>
            <button onClick={() => run(action)} disabled={busy !== null}>
              {busy === action ? "…" : LABEL[action]}
            </button>
          </p>
        ),
      )}
      {error && <p className="field-error">{error}</p>}
    </section>
  );
}
