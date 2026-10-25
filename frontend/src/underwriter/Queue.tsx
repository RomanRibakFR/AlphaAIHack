import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { QueueItem, StatusCode } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal, Stagger } from "../ui/Reveal";
import { dateTime, money, months } from "../lib/format";
import Grade from "./components/Grade";

const SECONDARY = "var(--color-light-text-secondary)";
const POLL_MS = 5000;

/**
 * Вкладки очереди.
 *
 * По умолчанию открыт ручной разбор — это и есть работа специалиста.
 * Остальные нужны на защите: по ним видно, что конвейер и правда
 * доводит заявки до выдачи, а не только копит их в очереди.
 */
const TABS: Array<{ status: StatusCode; label: string }> = [
  { status: "manual_review", label: "Ждут решения" },
  { status: "offer_proposed", label: "Ждут ответа клиента" },
  { status: "info_requested", label: "Запросили данные" },
  { status: "issued", label: "Выданы" },
  { status: "rejected", label: "Отказы" },
];

export default function Queue() {
  const [tab, setTab] = useState<StatusCode>("manual_review");
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** Сколько клиентов ждут ответа — показываем на ссылке в чаты. */
  const [unanswered, setUnanswered] = useState(0);

  const load = useCallback(async () => {
    try {
      setItems(await api.backoffice.queue(tab));
      setError(null);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [tab]);

  useEffect(() => {
    setItems(null);
    void load();
  }, [load]);

  // очередь пополняется сама, пока конвейер разбирает заявки
  useEffect(() => {
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    const count = async () => {
      try {
        const chats = await api.backoffice.chats();
        setUnanswered(chats.reduce((sum, c) => sum + (c.unread > 0 ? 1 : 0), 0));
      } catch {
        /* счётчик — украшение, без него очередь работает */
      }
    };
    void count();
    const timer = setInterval(() => void count(), POLL_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              Очередь заявок
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Заявки, которые конвейер не закрыл сам. Под каждой — почему она здесь.
            </Text>
          </div>

          <Link to="/underwriter/chats" className="uw-chats-link">
            Вопросы клиентов
            {unanswered > 0 && <span className="ch-badge">{unanswered}</span>}
          </Link>
        </div>
      </Reveal>

      <Reveal>
        <div className="cb-tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.status}
              role="tab"
              aria-selected={t.status === tab}
              className="cb-tab"
              onClick={() => setTab(t.status)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </Reveal>

      {error && (
        <Text view="primary-medium" color="var(--color-light-text-negative)">
          {error}
        </Text>
      )}

      {items === null && !error && (
        <div className="lp-skeleton mo-shimmer" style={{ minHeight: 200, borderRadius: 32 }} />
      )}

      {items !== null && items.length === 0 && (
        <Reveal>
          <section className="cb-card">
            <Text view="accent-primary-large" tag="h2">
              Здесь пусто
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Ни одной заявки в этом состоянии.
            </Text>
          </section>
        </Reveal>
      )}

      {items !== null && items.length > 0 && (
        <Stagger className="uw-queue" step={60}>
          {items.map((item) => (
            <Link key={item.id} to={`/underwriter/${item.id}`} className="uw-row mo-lift">
              <div className="uw-row-main">
                <Text view="accent-primary-medium" tag="div">
                  {item.company.name}
                </Text>
                <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
                  Заявка № {item.id} · {item.product.name}
                  {item.submitted_at && ` · отправлена ${dateTime(item.submitted_at)}`}
                </Text>
                {item.triggers.length > 0 && (
                  <ul className="uw-triggers">
                    {item.triggers.map((t) => (
                      <li key={t}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="uw-row-side">
                <Text view="accent-primary-medium" tag="div">
                  {money(item.amount)}
                </Text>
                <Text view="secondary-medium" color={SECONDARY}>
                  {months(item.term_months)}
                </Text>
                <Grade grade={item.grade} pd={item.pd} />
              </div>
            </Link>
          ))}
        </Stagger>
      )}
    </>
  );
}
