import { useCallback, useEffect, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { ActionCode, Application, FieldProblem, Product, StatusCode } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal } from "../ui/Reveal";
import { dateTime, money, months, rateRange } from "../lib/format";
import { HISTORY_TEXT } from "./content";
import ApplicationForm from "./components/ApplicationForm";
import StatusPanel from "./components/StatusPanel";
import { ContractPanel, OfferPanel, RejectionPanel } from "./components/Decision";
import InfoRequests from "./components/InfoRequests";

const SECONDARY = "var(--color-light-text-secondary)";
const POLL_MS = 3000;

/** Статусы, в которых заявка «у банка» и имеет смысл переспрашивать. */
const IN_PROGRESS: StatusCode[] = ["submitted", "validation", "checks", "scoring"];

/**
 * Подписи кнопок. Действия, которых здесь нет, не рисуются вовсе:
 * бэкенд может прислать и то, что кабинет ещё не умеет (например,
 * upload_document — загрузки документов пока нет), а пустая кнопка
 * хуже отсутствующей.
 */
const ACTION_LABEL: Partial<Record<ActionCode, string>> = {
  edit: "Редактировать",
  submit: "Отправить в банк",
  cancel: "Отозвать заявку",
  accept: "Принять предложение",
  decline: "Отказаться",
  sign: "Подписать договор",
  provide_info: "Я всё дополнил",
};

/** Главное действие на каждом шаге — его рисуем красной кнопкой. */
const PRIMARY: ActionCode[] = ["submit", "accept", "sign", "provide_info"];

export default function ApplicationCard() {
  const { id } = useParams();
  const appId = Number(id);

  const [app, setApp] = useState<Application | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [problems, setProblems] = useState<FieldProblem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<ActionCode | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  /** Выбранный вариант условий; null — основные условия предложения. */
  const [variant, setVariant] = useState<number | null>(null);
  const [signCode, setSignCode] = useState("");

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

  // пока заявка у банка — переспрашиваем статус
  const inProgress = app !== null && IN_PROGRESS.includes(app.status.code);
  useEffect(() => {
    if (!inProgress) return;
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [inProgress, load]);

  async function run(action: ActionCode) {
    setBusy(action);
    setActionError(null);
    setProblems([]);
    try {
      if (action === "submit") setApp(await api.submit(appId));
      else if (action === "cancel") setApp(await api.cancel(appId));
      else if (action === "accept") setApp(await api.accept(appId, variant ?? undefined));
      else if (action === "decline") setApp(await api.decline(appId));
      else if (action === "sign") setApp(await api.sign(appId, signCode.trim()));
      else if (action === "provide_info") setApp(await api.provideInfo(appId));
    } catch (e) {
      const err = e as ApiError;
      setActionError(err.message);
      if (err.problems.length > 0) setProblems(err.problems);
    } finally {
      setBusy(null);
    }
  }

  if (error) {
    return (
      <Text view="primary-medium" color="var(--color-light-text-negative)">
        {error}
      </Text>
    );
  }

  if (app === null) {
    return <div className="lp-skeleton mo-shimmer" style={{ minHeight: 320, borderRadius: 32 }} />;
  }

  const product = products.find((p) => p.code === app.product.code) ?? null;
  const editable = app.available_actions.includes("edit");
  const actions = app.available_actions.filter((a) => a !== "edit" && ACTION_LABEL[a]);
  /** Банк уже назвал условия — значит, прикидка по каталогу больше не нужна. */
  const decided = app.offer !== null || app.rejection !== null;

  return (
    <>
      <Link to="/cabinet" className="cb-back">
        ← Все заявки
      </Link>

      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              {app.product.name}
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Заявка № {app.id} · создана {dateTime(app.created_at)}
              {app.submitted_at && ` · отправлена ${dateTime(app.submitted_at)}`}
            </Text>
          </div>
        </div>
      </Reveal>

      <div className="cb-grid-2">
        <div style={{ display: "grid", gap: 24 }}>
          <Reveal>
            <StatusPanel app={app} />
          </Reveal>

          {app.info_requests.length > 0 && (
            <Reveal>
              <InfoRequests app={app} problems={problems} onUpdated={setApp} />
            </Reveal>
          )}

          {app.offer && (
            <Reveal>
              <OfferPanel offer={app.offer} chosen={variant} onChoose={setVariant} />
            </Reveal>
          )}

          {app.rejection && (
            <Reveal>
              <RejectionPanel rejection={app.rejection} />
            </Reveal>
          )}

          {(app.contract_number || (app.schedule && app.schedule.length > 0)) && (
            <Reveal>
              <ContractPanel
                contractNumber={app.contract_number}
                issuedAt={app.issued_at}
                schedule={app.schedule}
              />
            </Reveal>
          )}

          {editable ? (
            <Reveal>
              <ApplicationForm
                app={app}
                product={product}
                problems={problems}
                onFieldEdited={(field) =>
                  setProblems((prev) => prev.filter((p) => p.field !== field))
                }
                onSaved={setApp}
              />
            </Reveal>
          ) : (
            <Reveal>
              <section className="cb-card-white">
                {/* Пока решения нет, здесь прикидка по ставке «от». Как только банк
                    ответил, цифры решения живут в блоке предложения, а тут остаётся
                    только то, что человек просил, — иначе на экране две разные суммы
                    без объяснения, какая настоящая. */}
                <Text view="accent-primary-large" tag="h2">
                  {decided ? "Что вы просили" : "Параметры кредита"}
                </Text>
                <div className="cb-pairs" style={{ marginTop: 20 }}>
                  <div className="cb-pair">
                    <span>Сумма</span>
                    <span>{money(app.amount)}</span>
                  </div>
                  <div className="cb-pair">
                    <span>Срок</span>
                    <span>{months(app.term_months)}</span>
                  </div>
                  <div className="cb-pair">
                    <span>Цель</span>
                    <span>{app.purpose || "—"}</span>
                  </div>
                  {app.annual_revenue && (
                    <div className="cb-pair">
                      <span>Выручка за 12 месяцев</span>
                      <span>{money(app.annual_revenue)}</span>
                    </div>
                  )}
                  {!decided && product && (
                    <div className="cb-pair">
                      <span>Ставка</span>
                      <span>{rateRange(product.base_rate, product.max_rate)}</span>
                    </div>
                  )}
                  {!decided && (
                    <div className="cb-pair">
                      <span>Примерный платёж</span>
                      <span>{money(app.estimated_payment)} в месяц</span>
                    </div>
                  )}
                </div>
              </section>
            </Reveal>
          )}

          <Reveal>
            <section className="cb-card-white">
              <Text view="accent-primary-large" tag="h2">
                История
              </Text>
              {app.history.length === 0 ? (
                <Text view="primary-small" color={SECONDARY} style={{ marginTop: 12 }}>
                  Пока ничего не происходило.
                </Text>
              ) : (
                <ul className="cb-history" style={{ marginTop: 20 }}>
                  {app.history.map((h, i) => (
                    <li key={i}>
                      <span style={{ color: SECONDARY }}>{dateTime(h.created_at)}</span>
                      <span>
                        {HISTORY_TEXT[h.to_status]}
                        {h.comment && (
                          <span style={{ display: "block", color: SECONDARY, marginTop: 4 }}>
                            {h.comment}
                          </span>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </Reveal>
        </div>

        <Reveal delay={80}>
          <section className="cb-card">
            <Text view="accent-primary-large" tag="h2">
              Что дальше
            </Text>

            {app.deadline_at && actions.length > 0 && (
              <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 8 }}>
                Банк ждёт ответа до {dateTime(app.deadline_at)}.
              </Text>
            )}

            {/* Код подписания. В настоящем банке он пришёл бы в SMS, но кейс
                требует не выходить за пределы продукта — поэтому показываем
                его здесь же, рядом с полем ввода. */}
            {app.sign_code && (
              <div className="cb-sign" style={{ marginTop: 20 }}>
                <Text view="secondary-medium" color={SECONDARY}>
                  Код подтверждения
                </Text>
                <Text view="promo-h3" tag="div" className="cb-sign-code">
                  {app.sign_code}
                </Text>
                <Text view="secondary-medium" color={SECONDARY}>
                  В настоящем банке он пришёл бы в SMS. Введите его ниже, чтобы подписать
                  договор.
                </Text>
                <Input
                  label="Код из SMS"
                  block
                  value={signCode}
                  error={problems.find((p) => p.field === "code")?.message}
                  style={{ marginTop: 12 }}
                  onChange={(_, { value }) => setSignCode(value)}
                />
              </div>
            )}

            {actions.length === 0 ? (
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 12 }}>
                Сейчас от вас ничего не требуется.
              </Text>
            ) : (
              <div style={{ marginTop: 20, display: "grid", gap: 10 }}>
                {actions.map((action) => (
                  <Button
                    key={action}
                    view={PRIMARY.includes(action) ? "accent" : "secondary"}
                    size={48}
                    block
                    className="mo-press"
                    loading={busy === action}
                    disabled={action === "sign" && signCode.trim() === ""}
                    onClick={() => run(action)}
                  >
                    {ACTION_LABEL[action]}
                  </Button>
                ))}
              </div>
            )}

            {actionError && (
              <Text
                view="secondary-medium"
                color="var(--color-light-text-negative)"
                style={{ marginTop: 12 }}
              >
                {actionError}
              </Text>
            )}
          </section>
        </Reveal>
      </div>
    </>
  );
}
