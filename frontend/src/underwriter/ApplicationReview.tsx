import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { BackofficeApplication, Decision, UnderwriterDecision } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal } from "../ui/Reveal";
import { dateTime, money, months, rate } from "../lib/format";
import { CHECK_STATUS, LIMIT_BINDING, MANUAL_TRIGGERS, OUTCOME, SOURCES } from "./content";
import DecisionForm from "./components/DecisionForm";
import Scoring from "./components/Scoring";

const SECONDARY = "var(--color-light-text-secondary)";

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div className="cb-pair">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

/**
 * Разбор заявки специалистом.
 *
 * Слева — всё, на чём строится решение: анкета, что ответили источники,
 * оценка риска с разбором по признакам и рекомендация системы.
 * Справа — само решение. Порядок именно такой: сначала основания,
 * потом вывод, иначе экран подталкивает нажать кнопку не глядя.
 */
export default function ApplicationReview() {
  const { id } = useParams();
  const appId = Number(id);

  const [data, setData] = useState<BackofficeApplication | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.backoffice.application(appId));
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [appId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(body: UnderwriterDecision) {
    setBusy(true);
    setDecisionError(null);
    try {
      setData(await api.backoffice.decide(appId, body));
    } catch (e) {
      setDecisionError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Text view="primary-medium" color="var(--color-light-text-negative)">
        {error}
      </Text>
    );
  }

  if (data === null) {
    return <div className="lp-skeleton mo-shimmer" style={{ minHeight: 320, borderRadius: 32 }} />;
  }

  const { application: app, checks, decisions } = data;
  /**
   * Каждый блок берёт своё из того решения, где это есть.
   *
   * Решение специалиста не несёт ни признаков, ни триггеров, ни рекомендации —
   * после одобрения последнее решение пустое, и единый «последний» источник
   * обнулил бы весь разбор. А у заявки, где источник не ответил, оценка
   * не считалась вовсе: признаков нет, но объяснить, почему она здесь, надо.
   */
  const latest = (has: (d: Decision) => boolean) =>
    [...decisions].reverse().find(has) ?? null;

  const scored = latest((d) => Object.keys(d.features).length > 0);
  const flagged = latest((d) => d.manual_triggers.length > 0);
  const advised = latest((d) => d.recommendation !== null);
  const waiting = app.status.code === "manual_review";

  return (
    <>
      <Link to="/underwriter" className="cb-back">
        ← Вся очередь
      </Link>

      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              {app.company.name}
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Заявка № {app.id} · {app.product.name} · ИНН {app.company.inn}
              {app.submitted_at && ` · отправлена ${dateTime(app.submitted_at)}`}
            </Text>
          </div>
        </div>
      </Reveal>

      <div className="cb-grid-2">
        <div style={{ display: "grid", gap: 24 }}>
          <Reveal>
            <section className="cb-card">
              <Text view="promo-h3" tag="h2">
                {app.status.title}
              </Text>
              {flagged && (
                <>
                  <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 12 }}>
                    Почему заявка здесь
                  </Text>
                  <ul className="cb-list" style={{ marginTop: 8 }}>
                    {flagged.manual_triggers.map((t) => (
                      <li key={t}>{MANUAL_TRIGGERS[t] ?? t}</li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          </Reveal>

          <Reveal>
            <section className="cb-card-white">
              <Text view="accent-primary-large" tag="h2">
                Анкета клиента
              </Text>
              <div className="cb-pairs" style={{ marginTop: 20 }}>
                <Pair label="Сумма" value={money(app.amount)} />
                <Pair label="Срок" value={months(app.term_months)} />
                <Pair label="Цель" value={app.purpose || "—"} />
                <Pair label="Выручка за 12 месяцев" value={money(app.annual_revenue)} />
                {app.collateral_type && (
                  <Pair
                    label="Залог"
                    value={`${app.collateral_description || app.collateral_type} · ${money(
                      app.collateral_value,
                    )}`}
                  />
                )}
              </div>
              {app.documents.length > 0 && (
                <>
                  <Text view="accent-primary-medium" tag="h3" style={{ marginTop: 24 }}>
                    Документы
                  </Text>
                  <ul className="cb-list" style={{ marginTop: 8 }}>
                    {app.documents.map((d) => (
                      <li key={d.id}>
                        {d.filename} · загружен {dateTime(d.uploaded_at)}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          </Reveal>

          <Reveal>
            <section className="cb-card-white">
              <Text view="accent-primary-large" tag="h2">
                Что ответили источники
              </Text>
              <table className="cb-table" style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Источник</th>
                    <th>Ответ</th>
                    <th>Попыток</th>
                    <th>Время</th>
                  </tr>
                </thead>
                <tbody>
                  {checks.map((c) => {
                    const view = CHECK_STATUS[c.status] ?? { label: c.status, tone: "warn" };
                    return (
                      <tr key={c.source}>
                        <td>{SOURCES[c.source] ?? c.source}</td>
                        <td>
                          <span className="uw-check" data-tone={view.tone}>
                            {view.label}
                          </span>
                          {c.error && <div className="uw-feature-hint">{c.error}</div>}
                        </td>
                        <td>{c.attempts}</td>
                        <td>{dateTime(c.finished_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          </Reveal>

          {scored && (
            <Reveal>
              <Scoring decision={scored} />
            </Reveal>
          )}

          {advised?.recommendation && (
            <Reveal>
              <section className="cb-card-white">
                <Text view="accent-primary-large" tag="h2">
                  Рекомендация системы
                </Text>
                <div className="cb-pairs" style={{ marginTop: 20 }}>
                  <Pair label="Сумма" value={money(String(advised.recommendation.amount))} />
                  <Pair label="Срок" value={months(advised.recommendation.term_months)} />
                  <Pair label="Ставка" value={rate(String(advised.recommendation.rate))} />
                  <Pair
                    label="Платёж"
                    value={`${money(String(advised.recommendation.monthly_payment))} в месяц`}
                  />
                  {advised.max_amount && (
                    <Pair
                      label="Предельная сумма"
                      value={`${money(advised.max_amount)}${
                        advised.limit_binding
                          ? ` · ограничило: ${LIMIT_BINDING[advised.limit_binding] ?? advised.limit_binding}`
                          : ""
                      }`}
                    />
                  )}
                </div>
                {advised.recommendation.conditions.length > 0 && (
                  <ul className="cb-list" style={{ marginTop: 16 }}>
                    {advised.recommendation.conditions.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                )}
              </section>
            </Reveal>
          )}

          <Reveal>
            <section className="cb-card-white">
              <Text view="accent-primary-large" tag="h2">
                История решений
              </Text>
              <ul className="cb-history" style={{ marginTop: 20 }}>
                {decisions.map((d, i) => (
                  <li key={i}>
                    <span style={{ color: SECONDARY }}>{dateTime(d.created_at)}</span>
                    <span>
                      {OUTCOME[d.outcome] ?? d.outcome}
                      <span style={{ display: "block", color: SECONDARY, marginTop: 4 }}>
                        {d.decided_by === "underwriter" ? "специалист" : "система"}
                        {d.comment && ` · ${d.comment}`}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </Reveal>
        </div>

        <Reveal delay={80}>
          {waiting ? (
            <DecisionForm
              recommendation={advised?.recommendation ?? null}
              busy={busy}
              error={decisionError}
              onSubmit={decide}
            />
          ) : (
            <section className="cb-card">
              <Text view="accent-primary-large" tag="h2">
                Решение принято
              </Text>
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 12 }}>
                Заявка в состоянии «{app.status.title}». Разбирать её больше не нужно.
              </Text>
            </section>
          )}
        </Reveal>
      </div>
    </>
  );
}
