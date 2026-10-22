import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Actions from "../components/Actions";
import DraftForm from "../components/DraftForm";
import StatusBlock from "../components/StatusBlock";
import Timeline from "../components/Timeline";
import { ApiError, api } from "../api/client";
import type { Application, FieldProblem, Product, StatusCode } from "../api/types";
import { dateTime, money, months } from "../lib/format";

/** Статусы, в которых заявка «у банка» и мы ждём смены статуса. */
const IN_PROGRESS: StatusCode[] = ["submitted", "validation", "external_checks", "scoring"];

/** Статусы, где банк что-то предложил или сообщил, но полей для этого в API нет. */
const NEEDS_DECISION_DATA: StatusCode[] = ["approved", "counter_offer", "rejected", "needs_info"];

const POLL_MS = 3000;

export default function ApplicationCard() {
  const { id } = useParams();
  const appId = Number(id);

  const [app, setApp] = useState<Application | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [problems, setProblems] = useState<FieldProblem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setApp(await api.application(appId));
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [appId]);

  useEffect(() => {
    void load();
    api.products().then(setProducts).catch(() => setProducts([]));
  }, [load]);

  // пока заявка «в обработке» — переспрашиваем статус
  const inProgress = app !== null && IN_PROGRESS.includes(app.status.code);
  useEffect(() => {
    if (!inProgress) return;
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [inProgress, load]);

  if (error) return <p className="field-error">{error}</p>;
  if (app === null) return <p>Загружаем заявку…</p>;

  const editable = app.available_actions.includes("edit");

  return (
    <>
      <p>
        <Link to="/cabinet">← в кабинет</Link>
      </p>

      <section>
        <h2>
          Заявка № {app.id} · {app.product.name}
        </h2>
        <p className="muted">
          {app.company.name} · создана {dateTime(app.created_at)}
          {app.submitted_at && ` · отправлена ${dateTime(app.submitted_at)}`}
        </p>
      </section>

      <StatusBlock status={app.status} />

      {inProgress && (
        <section className="stub" data-why="статус не двинется — нет логики решения">
          <p>
            Заявка в обработке, экран опрашивает <code>GET /api/applications/{app.id}</code> каждые{" "}
            {POLL_MS / 1000} с. Но перевод <code>submitted → validation</code> делает «система», а
            запускать её пока некому: скоринга и решения на бэкенде нет. Заявка останется здесь
            навсегда.
          </p>
          <p className="muted">
            Отдельно надо договориться, как фронт узнаёт о смене статуса: поллинг, SSE или
            websocket.
          </p>
        </section>
      )}

      {NEEDS_DECISION_DATA.includes(app.status.code) && (
        <section className="stub" data-why="в API нет полей решения банка">
          <p>Для этого статуса нужно показать то, чего в ответе бэкенда нет:</p>
          <ul>
            <li>
              <b>одобрение / контрпредложение</b> — одобренная сумма, срок, ставка, до какого числа
              действует предложение
            </li>
            <li>
              <b>отказ</b> — причина в понятных клиенту словах
            </li>
            <li>
              <b>нужно дополнить</b> — чего именно не хватает и куда это донести
            </li>
          </ul>
          <p className="muted">Просить у Ромы расширение ApplicationOut.</p>
        </section>
      )}

      {editable ? (
        <DraftForm
          app={app}
          products={products}
          problems={problems}
          onFieldEdited={(field) =>
            setProblems((prev) => prev.filter((p) => p.field !== field))
          }
          onSaved={setApp}
        />
      ) : (
        <section>
          <h3>Заявка</h3>
          <table>
            <tbody>
              <tr>
                <th>Продукт</th>
                <td>{app.product.name}</td>
              </tr>
              <tr>
                <th>Сумма</th>
                <td>{money(app.amount)}</td>
              </tr>
              <tr>
                <th>Срок</th>
                <td>{months(app.term_months)}</td>
              </tr>
              <tr>
                <th>Цель</th>
                <td>{app.purpose || "—"}</td>
              </tr>
              <tr>
                <th>Примерный платёж</th>
                <td>{money(app.estimated_payment)} в месяц</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      <Actions app={app} onDone={setApp} onProblems={setProblems} />

      <Timeline history={app.history} />
    </>
  );
}
